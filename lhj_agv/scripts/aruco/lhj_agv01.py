import cv2
import cv2.aruco as aruco
import numpy as np
from pymycobot.myagv import MyAgv
import threading
import time
import os

# AGV 제어를 위한 객체 생성
state = threading.Lock()
agv = MyAgv("/dev/ttyAMA2", 115200)

# 마지막 오프셋과 각도를 저장하는 변수
last_offset, last_angle = None, None

# 보정 행렬과 왜곡 계수를 불러옵니다.
camera_matrix = np.load(r"image/camera_matrix.npy")
dist_coeffs = np.load(r"image/dist_coeffs.npy")

print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

# 3D 측정에 사용할 Aruco 마커 딕셔너리를 선택합니다.
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
parameters = aruco.DetectorParameters()

# 비디오 캡처를 시작합니다.
cap = cv2.VideoCapture(0)

# 마커의 실제 크기를 정확히 설정합니다 (예: 0.04미터 = 4cm).
marker_length = 0.055  # 마커의 실제 크기 (미터 단위)

# 성능 최적화를 위한 파라미터
MIN_CONTOUR_AREA = 500  # 최소 윤곽선 면적 설정
SMALL_KERNEL = np.ones((3, 3), np.uint8)
LARGE_KERNEL = np.ones((5, 5), np.uint8)

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
            angle = 0

            # 라인 인식 시각화
            cv2.rectangle(roi, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.line(roi, (line_center, y), (line_center, y + h), (255, 0, 0), 2)
            return offset, angle
    return None, None

# AGV 이동 명령 실행
def execute_command(offset, angle):
    """AGV 이동 명령 실행"""
    c_offset = int(offset)
    with state:
        if c_offset is None:
            print("라인을 찾지 못했습니다.")
            return  # 명령 실행 중단
        # 회전 제어
        #if abs(offset) > 120:
        if abs(c_offset) > 120:
            speed_factor = max(1.0, min(4.0, abs(c_offset) / 100))  # 많이 벗어날수록 더 큰 회전 속도, 회전 민감도 감소
            rotation_speed = int(np.clip(30 * speed_factor, 1, 127))  # 회전 속도 조절
            if c_offset < 0:
                print(f"왼쪽 회전: {rotation_speed}")
                while abs(c_offset) > 10:
                    agv.counterclockwise_rotation(rotation_speed, 0.11)
                    ret, frame = cap.read()
                    if not ret:
                        print("카메라 오류 발생")
                        break
                    c_offset, angle = process_frame(frame)
            else:
                print(f"오른쪽 회전: {rotation_speed}")
                while abs(c_offset) > 40:
                    agv.clockwise_rotation(rotation_speed, 0.11)
                    ret, frame = cap.read()
                    if not ret:
                        print("카메라 오류 발생")
                        break
                    c_offset, angle = process_frame(frame)
        # 직진 제어
        speed_factor = max(0.8, min(1.0, abs(c_offset) / 150))  # 직진성을 높이기 위해 속도 범위 조정
        go_ahead_speed = int(np.clip(30 / speed_factor, 1, 127))
        print(f"직진: {go_ahead_speed}")
        agv.go_ahead(min(go_ahead_speed + 50, 127), 0.1)

# Aruco 마커 ID와 거리에 따라 AGV 제어
def control_agv_based_on_marker(id, distance):
    """
    Aruco 마커 ID와 거리에 따라 AGV를 제어합니다.
    """
    if distance <= 0.3:
        if id in [1, 5]:
            # ID 1, 5: AGV 정지
            print(f"ID {id} 감지됨 - AGV 정지")
            agv.go_ahead(0, 0.1)
        elif id in [2, 4]:
            # ID 2, 4: AGV 전진
            print(f"ID {id} 감지됨 - AGV 전진")
            execute_command(last_offset, last_angle)  # 속도 50으로 1초간 전진
        elif id == 3:
            # ID 3: AGV 정지
            print("ID 3 감지됨 - AGV 정지")
            agv.go_ahead(0, 0.1)
    else:
        print(f"ID {id} 감지됨 - 거리 멀음, 동작 없음")

# 카메라에서 프레임을 읽고 AGV 제어를 수행하는 함수
def camera_thread():
    global last_offset, last_angle
    setup_display()

    while True:
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            print("카메라 오류 발생")
            break

        offset, angle = process_frame(frame)
        #last_offset, last_angle = offset, angle
        if offset is not None:
            print(f"Offset: {offset}, Angle: {angle}")
            execute_command(offset, angle)
            last_offset, last_angle = offset, angle
        #else :
        #    execute_command(last_offset, last_angle)

        # 그레이스케일로 변환합니다.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 마커 코너좌표, ID, 거부된 마커 = 마커 탐지()
        corners, ids, rejectedImgPoints = cv2.aruco.detectMarkers(
            gray, aruco_dict, parameters=parameters
        )

        if ids is not None:
            # 각 마커에 대해 루프를 돌면서 포즈를 추정합니다.
            for i in range(len(ids)):
                # 회전벡터(rvec), 변환벡터(tvec)
                rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
                    corners[i], marker_length, camera_matrix, dist_coeffs
                )
                # 변환벡터 tvec의 크기를 계산하여 거리를 계산함
                distance = np.linalg.norm(tvec)

                # 마커의 경계와 축을 그립니다.
                aruco.drawDetectedMarkers(frame, corners)
                cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, 0.1)

                # 거리를 화면에 출력합니다.
                cv2.putText(
                    frame,
                    f"ID: {ids[i][0]} Distance: {distance:.3f} m",
                    (10, 30 + i * 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )

                # AGV 제어 함수 호출
                control_agv_based_on_marker(ids[i][0], distance)

        cv2.imshow("Line Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_agv()
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
