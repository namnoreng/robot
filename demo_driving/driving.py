import cv2
import cv2.aruco as aruco
import numpy as np
import serial
import time

# 마커 크기 설정
marker_length = 0.05

# npy 파일 불러오기
camera_matrix = np.load(r"camera_value/camera_back_matrix.npy")
dist_coeffs = np.load(r"camera_value/dist_back_coeffs.npy")

# 보정 행렬과 왜곡 계수를 불러옵니다.
print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

cv_version = cv2.__version__.split(".")
if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
    print("Using OpenCV 3.x")
else:
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters()
    print("Using OpenCV 4.x")

def flush_camera(cap, num=5):
    for _ in range(num):
        cap.read()

def initialize_robot(cap, aruco_dict, parameters, marker_index, serial_server):
    FRAME_CENTER_X = 640   # 1280x720 해상도 기준
    FRAME_CENTER_Y = 360
    CENTER_TOLERANCE = 30  # 중앙 허용 오차 (픽셀)
    ANGLE_TOLERANCE = 5    # 각도 허용 오차 (도)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("카메라 프레임을 읽지 못했습니다.")
            continue

        result = find_aruco_info(
            frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length
        )
        print("find_aruco_info result:", result)
        distance, (x_angle, y_angle, z_angle), (center_x, center_y) = result

        if distance is not None:
            dx = center_x - FRAME_CENTER_X
            angle_error = z_angle

            print(f"중심 오차: ({dx}), 각도 오차: {angle_error:.2f}")

            # 1. 회전값 먼저 맞추기
            if abs(angle_error) > ANGLE_TOLERANCE:
                if angle_error > 0:
                    print("좌회전")
                    serial_server.write('3'.encode())
                else:
                    print("우회전")
                    serial_server.write('4'.encode())
                continue  # 회전이 맞을 때까지 중앙값 동작으로 넘어가지 않음

            # 2. 회전이 맞으면 중앙값 맞추기
            if abs(dx) > CENTER_TOLERANCE:
                if dx > 0:
                    print("오른쪽으로 이동")
                    serial_server.write('6'.encode())
                else:
                    print("왼쪽으로 이동")
                    serial_server.write('5'.encode())
                continue  # 중앙이 맞을 때까지 반복

            # 3. 둘 다 맞으면 정지
            print("초기화 완료: 중앙+수직")
            serial_server.write('9'.encode())  # 정지 명령
            break

        else:
            print("마커를 찾지 못했습니다.")
            serial_server.write('9'.encode())  # 마커를 찾지 못했을 때 정지 명령

        #cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()

# 직진 아르코마커 인식
def driving(cap, aruco_dict, parameters, marker_index):
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # find_aruco_info 함수로 정보 추출
        distance, (x_angle, y_angle, z_angle), (center_x, center_y) = find_aruco_info(
            frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length
        )

        # 정보가 있으면 출력 및 동작
        if distance is not None:
            print(f"ID: {marker_index} Rotation (X, Y, Z): ({x_angle:.2f}, {y_angle:.2f}, {z_angle:.2f})")
            print(f"ID: {marker_index} Distance: {distance:.3f} m, Center: ({center_x}, {center_y})")

            # 시각화
            cv2.putText(
                frame,
                f"ID: {marker_index} Distance: {distance:.3f} m",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            # 원하는 거리 이내에 들어오면 종료
            if distance < 0.4:
                break

        #cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()

def find_aruco_info(frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length):
    """
    frame: 입력 이미지 (BGR)
    aruco_dict, parameters: 아르코 딕셔너리 및 파라미터
    marker_index: 찾고자 하는 마커 ID
    camera_matrix, dist_coeffs: 카메라 보정값
    marker_length: 마커 실제 길이(m)
    반환값: (distance, (x_angle, y_angle, z_angle), (center_x, center_y)) 또는 (None, (None, None, None), (None, None))
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        for i in range(len(ids)):
            if ids[i][0] == marker_index:
                # 포즈 추정 (corners[i] → [corners[i]])
                cv_version = cv2.__version__.split(".")
                if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
                    # OpenCV 3.2.x 이하
                    rvecs, tvecs = aruco.estimatePoseSingleMarkers(
                        np.array([corners[i]]), marker_length, camera_matrix, dist_coeffs
                    )
                else:
                    # OpenCV 3.3.x 이상 또는 4.x
                    rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
                        np.array([corners[i]]), marker_length, camera_matrix, dist_coeffs
                    )
                distance = np.linalg.norm(tvecs[0][0])

                # 회전 행렬 및 각도
                rotation_matrix, _ = cv2.Rodrigues(rvecs[0][0])
                sy = np.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
                singular = sy < 1e-6

                if not singular:
                    x_angle = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
                    y_angle = np.arctan2(-rotation_matrix[2, 0], sy)
                    z_angle = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
                else:
                    x_angle = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
                    y_angle = np.arctan2(-rotation_matrix[2, 0], sy)
                    z_angle = 0

                x_angle = np.degrees(x_angle)
                y_angle = np.degrees(y_angle)
                z_angle = np.degrees(z_angle)

                # 중심점 좌표 계산
                c = corners[i].reshape(4, 2)
                center_x = int(np.mean(c[:, 0]))
                center_y = int(np.mean(c[:, 1]))

                return distance, (x_angle, y_angle, z_angle), (center_x, center_y)
    # 못 찾으면 None 반환
    return None, (None, None, None), (None, None)
