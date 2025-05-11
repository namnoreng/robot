import cv2
import cv2.aruco as aruco
import numpy as np
import time
from pymycobot.myagv import MyAgv

# AGV 초기화
agv = MyAgv("/dev/ttyAMA2", 115200)

# ArUco 설정
ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
ARUCO_PARAMETERS = aruco.DetectorParameters_create()
# 카메라 보정 데이터 로드
camera_matrix = np.load("/home/er/myagv_ws/src/myagv_navigation/scripts/aruco/image/camera_matrix.npy")
dist_coeffs = np.load("/home/er/myagv_ws/src/myagv_navigation/scripts/aruco/image/dist_coeffs.npy")

print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

# 도킹 임계값 설정
CENTER_THRESHOLD_PIXELS = 10  # X축 정렬을 위한 픽셀 허용 오차
ANGLE_THRESHOLD_DEGREES = 1  # 각도 정렬 허용 오차 (도 단위)
BRIGHTNESS_THRESHOLD = 1  # 도킹 완료를 판단할 밝기 임계값 (0~255)
APPROACH_STEP = 0.5  # AGV 전진 단계 크기 (미터)

def forward(duration, speed=20):
    """AGV 전진"""
    print(f"AGV 전진 {duration}초 동안.")
    agv.go_ahead(speed, duration)

def rotate(direction, duration, speed=20):
    """AGV 회전"""
    print(f"AGV {direction} 방향으로 {duration}초 동안 회전.")
    if direction == "counter_clockwise":
        agv.counterclockwise_rotation(speed, duration)
    elif direction == "clockwise":
        agv.clockwise_rotation(speed, duration)

def retreat(duration, speed=20):
    """AGV 후진"""
    print(f"AGV 후진 {duration}초 동안.")
    agv.retreat(speed, timeout=duration)

def pan_left(duration, speed=20):
    """AGV 왼쪽 이동"""
    print(f"AGV 왼쪽으로 {duration}초 동안 이동.")
    agv.pan_left(speed, duration)

def pan_right(duration, speed=20):
    """AGV right 이동"""
    print(f"AGV right {duration}초 동안 이동.")
    agv.pan_right(speed, duration)

def agv_stop():
    """AGV stop"""
    print(f"AGV stop")
    agv.stop()

def calculate_marker_properties(frame, corners):
    """
    ArUco 마커의 중심 좌표와 카메라 대비 각도를 계산합니다.
    - 마커 중심 (X, Y 좌표)
    - 마커의 카메라 대비 기울기 (각도)
    """
    top_left, top_right, bottom_right, bottom_left = corners
    marker_center = (
        int((top_left[0] + bottom_right[0]) / 2),
        int((top_left[1] + bottom_right[1]) / 2)
    )
    dx = top_right[0] - top_left[0]
    dy = top_right[1] - top_left[1]
    marker_angle = np.degrees(np.arctan2(dy, dx))  # 각도를 도 단위로 계산
    return marker_center, marker_angle

def calculate_brightness(frame):
    """
    현재 프레임의 평균 밝기를 계산합니다.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)

def align_to_marker(marker_center, frame_center, marker_angle):
    """
    ArUco 마커 중심과 화면 중심을 정렬하고, 마커 각도를 정렬합니다.
    """
    #     # 각도 정렬
    # if abs(marker_angle) > ANGLE_THRESHOLD_DEGREES:
    #     if marker_angle > 0:
    #         print(f"마커 각도 {marker_angle:.2f}°. 시계 방향으로 회전.")
    #         agv.clockwise_rotation(10, abs(marker_angle) / 180)
    #     else:
    #         print(f"마커 각도 {marker_angle:.2f}°. 반시계 방향으로 회전.")
    #         agv.counterclockwise_rotation(10, abs(marker_angle) / 180)

    # X축 정렬
    x_diff_pixels = marker_center[0] - frame_center[0]
    if abs(x_diff_pixels) > CENTER_THRESHOLD_PIXELS:
        if x_diff_pixels > 0:
            print(f"마커가 화면 중심의 오른쪽에 있습니다. {x_diff_pixels}px 만큼 오른쪽으로 이동.")
            agv.clockwise_rotation(40, abs(x_diff_pixels) / 500)
        else:
            print(f"마커가 화면 중심의 왼쪽에 있습니다. {x_diff_pixels}px 만큼 왼쪽으로 이동.")
            agv.counterclockwise_rotation(40, abs(x_diff_pixels) / 500)



def approach_marker(z_distance):
    """
    ArUco 마커와의 Z축 거리를 기반으로 AGV가 전진하도록 설정합니다.
    """
    if z_distance > 0:  # 거리 확인 (필요 시 사용)
        print(f"마커로 접근 중: {z_distance:.2f}m 남음.")
        agv.go_ahead(10, APPROACH_STEP)  # 작은 단계로 전진
    else:
        print("마커에 도달했습니다. 도킹 완료.")
        agv.stop()


def detect_and_dock():
    """
    ArUco 마커를 탐지하고, 정렬 및 도킹을 수행합니다.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다. 연결 상태를 확인하세요.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("카메라에서 프레임을 가져오지 못했습니다.")
                break

            # 현재 프레임 밝기 계산
            brightness = calculate_brightness(frame)
            print(f"현재 프레임 밝기: {brightness:.2f}")

            # 밝기가 임계값 이하라면 도킹 완료
            if brightness < BRIGHTNESS_THRESHOLD:
                print("화면이 어두워졌습니다. 도킹 완료.")
                agv.stop()
                break

            # 화면 중심 계산
            frame_height, frame_width = frame.shape[:2]
            frame_center = (frame_width // 2, frame_height // 2)

            # 그레이스케일로 변환하고 ArUco 마커 탐지
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = aruco.detectMarkers(gray, ARUCO_DICT, parameters=ARUCO_PARAMETERS)

            if ids is not None:
                aruco.drawDetectedMarkers(frame, corners, ids)

                # 탐지된 모든 마커의 정보를 수집
                detected_markers = [{'id': ids[i][0], 'corners': corners[i][0]} for i in range(len(ids))]

                # 가장 가까운 마커 탐지
                closest_marker = detected_markers[0]
                marker_center, marker_angle = calculate_marker_properties(frame, closest_marker['corners'])
                rvec, tvec, _ = aruco.estimatePoseSingleMarkers([closest_marker['corners']], 0.05, camera_matrix, dist_coeffs)
                z_distance = tvec[0, 0, 2]  # Z축 거리 (미터 단위)

                cv2.circle(frame, marker_center, 5, (0, 255, 0), -1)  # 마커 중심 (녹색)
                print(f"마커 중심: {marker_center}, 화면 중심: {frame_center}")
                print(f"마커 각도: {marker_angle:.2f}°, Z 거리: {z_distance:.2f}m")

                # 마커에 정렬
                align_to_marker(marker_center, frame_center, marker_angle)

                # 마커로 접근
                approach_marker(z_distance)

            else:
                print("마커를 찾는 중...")
                cv2.putText(
                    frame, "Searching for marker...", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
                )
                #miss detecting
                print("little forward")
                agv.go_ahead(10, APPROACH_STEP)

            # 프레임 디스플레이
            cv2.imshow("ArUco Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # 'q'를 눌러 종료
                agv.stop()
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()




def detect_and_dock_with_distance(stop_distance=0.8):
    """
    ArUco 마커를 탐지하고, 설정된 거리에서 멈추도록 정렬 및 도킹을 수행합니다.
    
    Args:
        stop_distance (float): AGV가 멈출 Z축 거리 (미터 단위)
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다. 연결 상태를 확인하세요.")
        return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("카메라에서 프레임을 가져오지 못했습니다.")
                break

            # 화면 중심 계산
            frame_height, frame_width = frame.shape[:2]
            frame_center = (frame_width // 2, frame_height // 2)

            # 그레이스케일로 변환 및 ArUco 마커 탐지
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = aruco.detectMarkers(gray, ARUCO_DICT, parameters=ARUCO_PARAMETERS)

            if ids is not None:
                aruco.drawDetectedMarkers(frame, corners, ids)
                detected_markers = [{'id': ids[i][0], 'corners': corners[i][0]} for i in range(len(ids))]

                # 가장 가까운 마커 탐지
                closest_marker = detected_markers[0]
                rvec, tvec, _ = aruco.estimatePoseSingleMarkers([closest_marker['corners']], 0.05, camera_matrix, dist_coeffs)
                z_distance = tvec[0, 0, 2]  # Z축 거리 (미터 단위)

                print(f"마커 Z 거리: {z_distance:.2f}m")

                # ArUco 마커가 설정된 거리 이내에 있을 경우 AGV 정지
                if z_distance <= stop_distance:
                    print(f"목표 거리 {stop_distance:.2f}m에 도달했습니다. 도킹 중지.")
                    agv.stop()
                    return True

                # 마커 중심 정렬 및 접근
                marker_center, marker_angle = calculate_marker_properties(frame, closest_marker['corners'])
                align_to_marker(marker_center, frame_center, marker_angle)
                approach_marker(z_distance)

            else:
                print("마커를 찾는 중...")
                cv2.putText(frame, "Searching for marker...", (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # 탐지 실패 시 약간 전진
                agv.go_ahead(10, 0.1)

            # 프레임 디스플레이
            cv2.imshow("ArUco Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # 'q'를 눌러 종료
                agv.stop()
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return False

