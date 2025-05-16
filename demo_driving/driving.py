import cv2
import cv2.aruco as aruco
import numpy as np

# 마커 크기 설정
marker_length = 0.05

# npy 파일 불러오기
camera_matrix = np.load(r"camera_value/camera_back_matrix.npy")
dist_coeffs = np.load(r"camera_value/dist_back_coeffs.npy")

# 보정 행렬과 왜곡 계수를 불러옵니다.
print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

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

        cv2.imshow("frame", frame)
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
                # 포즈 추정
                rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
                    corners[i], marker_length, camera_matrix, dist_coeffs
                )
                distance = np.linalg.norm(tvec)

                # 회전 행렬 및 각도
                rotation_matrix, _ = cv2.Rodrigues(rvec)
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
