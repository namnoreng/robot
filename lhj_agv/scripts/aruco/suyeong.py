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

# 마지막 오프셋과 각도를 저장하는 변수
last_offset, last_angle = None, None

# 카메라 초기화 (비디오 캡처 오브젝트를 전역으로 생성)
cap = cv2.VideoCapture(0)

# 성능 최적화를 위한 파라메터
MIN_CONTOUR_AREA = 500  # 최소 윤각선 면적 설정
LARGE_KERNEL = np.ones((5, 5), np.uint8)

# AGV 제조를 위한 임계값 설정
OFFSET_THRESHOLD = 120
SMALL_OFFSET_THRESHOLD = 40

# 보정 행렬과 왜곡 계수를 불러옵니다.
camera_matrix = np.load(r"image/camera_matrix.npy")
dist_coeffs = np.load(r"image/dist_coeffs.npy")

print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

# ArUco 마커 정식
ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
ARUCO_PARAMETERS = aruco.DetectorParameters()

# AGV 제어 상태 변수
global stop_signal, avoid_flag
stop_signal = False
avoid_flag = False

# 디스플레이 설정 확인
def setup_display():
    if os.environ.get('DISPLAY', '') == '':
        print('No display found. Using :0.0')
        os.environ['DISPLAY'] = ':0.0'

# 프레임에서 라인을 검출하고 오프셋과 각도를 계산
def process_frame(frame):
    height, width, _ = frame.shape
    roi = frame[height // 2:, :]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_red = np.array([0, 50, 50], dtype=np.uint8)
    upper_red = np.array([10, 255, 255], dtype=np.uint8)
    red_mask = cv2.inRange(hsv, lower_red, upper_red)
    morphed = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, LARGE_KERNEL)

    contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest_contour) > MIN_CONTOUR_AREA:
            x, y, w, h = cv2.boundingRect(largest_contour)
            line_center = x + w // 2
            offset = line_center - (width // 2)

            # 라인 인식 시각화
            cv2.rectangle(roi, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.line(roi, (line_center, y), (line_center, y + h), (255, 0, 0), 2)
            return offset, 0
    return None, None

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
            # ArUco 마커가 0.7m 이내에 있을 경우 AGV 정지 신호 설정
            if distance <= 0.8:
                if ids[i][0] in [3]:
                    stop_signal = True
                    print(f"ID {ids[i][0]} 감지됨 - AGV 정지 (0.7m 이내)")
                elif ids[i][0] in [2, 4]:
                    stop_signal = False
                    print(f"ID {ids[i][0]} 감지됨 - AGV 재시작")
                elif ids[i][0] in [1] and not avoid_flag:
                    avoid_flag = True
                    print(f"ID {ids[i][0]} 감지됨 - AGV 회피기동 시작")
                    agv.pan_right(127, 0.7)
                    agv.go_ahead(127, 1.0)
                    agv.pan_left(127, 0.75)
                    #avoid_flag = False
                    print(f"ID {ids[i][0]} 감지됨 - AGV 회피기동 완료")
                elif ids[i][0] in [5] and not avoid_flag:
                    avoid_flag = True
                    print(f"ID {ids[i][0]} 감지됨 - AGV 회피기동 시작")
                    agv.pan_right(127, 0.7)
                    agv.go_ahead(127, 0.9)
                    agv.pan_left(127, 0.75)
                    #avoid_flag = False
                    print(f"ID {ids[i][0]} 감지됨 - AGV 회피기동 완료")
    else:
        # ArUco 마커가 감지되지 않으면 회피 플래그 해제
        avoid_flag = False
    return ids, corners

# AGV 이동 메인 명령 실행
def execute_command(offset):
    with state:
        if stop_signal:
            stop_agv()  # AGV 정지
            return

        if offset is None:
            if last_offset is not None:
                print("마지막 인식한 정보로 이동합니다.")
                offset = last_offset
            else:
                print("라인을 찾지 못했습니다.")
                return
        avoid_flag = False
        if abs(offset) > OFFSET_THRESHOLD:
            speed_factor = min(4.0, abs(offset) / 100)
            rotation_speed = int(np.clip(30 * speed_factor, 1, 127))
            if offset < 0:
                print(f"왼쪽 회전: {rotation_speed}")
                agv.counterclockwise_rotation(rotation_speed + 30, 0.1)
            else:
                print(f"오른쪽 회전: {rotation_speed}")
                agv.clockwise_rotation(rotation_speed + 30, 0.1)
        else:
            speed_factor = max(0.8, min(1.0, abs(offset) / 150))
            go_ahead_speed = int(np.clip(30 / speed_factor, 1, 127))
            print(f"직진: {go_ahead_speed}")
            agv.go_ahead(min(go_ahead_speed + 60, 127), 0.1)

# 카메라에서 프레임을 읽고 AGV 제어를 수행하는 함수
def camera_thread():
    global last_offset, last_angle, stop_signal
    setup_display()

    while True:
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            print("카메라 오류 발생")
            break

        # ArUco 마커 인식
        detect_aruco_markers(frame)

        # 라인 인식 및 AGV 제어
        offset, angle = process_frame(frame)
        if offset is not None:
            last_offset, last_angle = offset, angle

        # AGV 제어 명령을 별도의 스레드로 실행하여 카메라 프레임 처리를 방해하지 않도록 수정
        if not stop_signal:
            command_thread = threading.Thread(target=execute_command, args=(offset if offset is not None else last_offset,))
            command_thread.start()
            command_thread.join()  # 명령이 끝날 때까지 기다림으로써 명령이 제대로 수행되도록 수정

        # 화면 표시
        cv2.imshow("Line Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_signal = True
            agv.stop()  # 종료 시 AGV 정지
            break

        print(f"Frame 처리 시간: {time.time() - start_time:.4f}초")

    cap.release()
    cv2.destroyAllWindows()

# AGV 정지
def stop_agv():
    with state:
        agv.stop()
    print("AGV 정지")

# 카메라 스레드 실행
camera_thread = threading.Thread(target=camera_thread)
camera_thread.start()
camera_thread.join()
