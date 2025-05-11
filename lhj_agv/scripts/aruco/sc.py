import cv2
import cv2.aruco as aruco
import numpy as np
from pymycobot.myagv import MyAgv
import threading
import time
import os

# AGV 권리를 위한 Lock
state = threading.Lock()
agv = MyAgv("/dev/ttyAMA2", 115200)

# 카메라 초기화 (비디오 캡처 오브젝트를 전역으로 생성)
cap = cv2.VideoCapture(0)

# 보정 행렬과 왜곡 계수를 불러옵니다.
camera_matrix = np.load(r"image/camera_matrix.npy")
dist_coeffs = np.load(r"image/dist_coeffs.npy")

print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

# ArUco 마커 설정
ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
ARUCO_PARAMETERS = aruco.DetectorParameters_create()

# 카메라 해상도 설정
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # 너비 설정 (예: 640px)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # 높이 설정 (예: 480px)

# AGV 제어 상태 변수
global stop_signal, avoid_flag
stop_signal = False
avoid_flag = False

# 디스플레이 설정 확인
def setup_display():
    if os.environ.get('DISPLAY', '') == '':
        print('No display found. Using :0.0')
        os.environ['DISPLAY'] = ':0.0'

# ArUco 마커 검색 및 신호 처리
def detect_aruco_markers(frame):
    global stop_signal, avoid_flag
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = aruco.detectMarkers(gray, ARUCO_DICT, parameters=ARUCO_PARAMETERS)
    if ids is not None:
        for i in range(len(ids)):
            rvec, tvec, _ = aruco.estimatePoseSingleMarkers(corners[i], 0.04, camera_matrix, dist_coeffs)
            distance = np.linalg.norm(tvec)
            aruco.drawDetectedMarkers(frame, corners)
            cv2.putText(frame, f"ID: {ids[i][0]} Distance: {distance:.3f} m", (10, 50 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # ArUco 마커 1번이 0.8m 이내에 감지되었을 때 AGV 직진 및 좌회전 동작 수행
            if distance <= 2 and ids[i][0] == 1 and not avoid_flag:
                avoid_flag = True
                print(f"ID {ids[i][0]} 감지됨 - AGV 직진 90cm 후 좌회전")

                agv.stop()
                time.sleep(10)

                agv.counterclockwise_rotation(10, 0.5)  # 좌회전 90도
                time.sleep(0.5)

                agv.go_ahead(30, 2.0)  # 약 90cm 직진
                time.sleep(2)           # 직진 시간이 완료될 때까지 대기
                agv.counterclockwise_rotation(60, 1.5)  # 좌회전 90도
                time.sleep(1)           # 회전 시간이 완료될 때까지 대기

                agv.go_ahead(30, 2.0)  # 약 90cm 직진
                time.sleep(2)
                print(f"ID {ids[i][0]} 감지됨 - AGV 직진 및 좌회전 완료")
            # ArUco 마커 2번이 1.5m 이내에 감지되었을 때 AGV 좌회전 90도 후 직진 1m 동작 수행
            elif distance <= 2 and ids[i][0] == 2 and not avoid_flag:
                avoid_flag = True
                print(f"ID {ids[i][0]} 감지됨 - AGV 좌회전 후 1m 직진")

                agv.stop()
                time.sleep(1)

                agv.counterclockwise_rotation(90, 1.5)  # 좌회전 90도
                time.sleep(1.5)

                agv.go_ahead(30, 3.0)  # 1m 직진
                time.sleep(2)
                print(f"ID {ids[i][0]} 감지됨 - AGV 좌회전 후 직진 완료")
            # ArUco 마커 3번이 2.5m 이내에 감지되었을 때 우회전 90도, 직진 90cm, 좌회전 90도, 직진 30cm, 우회전 90도
            elif distance <= 2.5 and ids[i][0] == 3 and not avoid_flag:
                avoid_flag = True
                print(f"ID {ids[i][0]} 감지됨 - AGV 우회전, 직진 90cm, 좌회전, 직진 30cm, 우회전")

                agv.stop()
                time.sleep(1)

                agv.clockwise_rotation(90, 1.5)  # 우회전 90도
                time.sleep(1.5)

                agv.go_ahead(30, 0.9)  # 90cm 직진
                time.sleep(1.8)

                agv.counterclockwise_rotation(90, 1.5)  # 좌회전 90도
                time.sleep(1.5)

                agv.go_ahead(30, 0.3)  # 30cm 직진
                time.sleep(1)

                agv.clockwise_rotation(90, 1.5)  # 우회전 90도
                time.sleep(1.5)
                print(f"ID {ids[i][0]} 감지됨 - AGV 우회전, 직진 90cm, 좌회전, 직진 30cm, 우회전 완료")
                 
    else:
        avoid_flag = False
    return ids, corners

# AGV 이동 제어
def stop_agv():
    with state:
        agv.stop()
    print("AGV 정지")

# 카메라에서 프레임을 읽고 AGV 제어를 수행하는 함수
def camera_thread():
    global stop_signal, avoid_flag
    setup_display()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("카메라 오류 발생")
            break

        # ArUco 마커 인식
        detect_aruco_markers(frame)

        # 화면 표시
        cv2.imshow("ArUco Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_signal = True
            stop_agv()  # 종료 시 AGV 정지
            break

    cap.release()
    cv2.destroyAllWindows()

# 카메라 스레드 실행
camera_thread = threading.Thread(target=camera_thread)
camera_thread.start()
camera_thread.join()
