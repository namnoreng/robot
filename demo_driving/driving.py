import cv2
import cv2.aruco as aruco
import numpy as np

# 보정 행렬과 왜곡 계수를 불러옵니다.
camera_matrix = np.load(r"aruco/image_back/camera_back_matrix.npy")
dist_coeffs = np.load(r"aruco/image_back/dist_back_coeffs.npy")

print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

# 마커의 실제 크기를 정확히 설정합니다 (예: 0.08미터 = 8cm).
marker_length = 0.05 / 2.54  # 마커의 실제 크기 (미터 단위)

def driving(cap, aruco_dict, parameters):
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejectedImgPoints = cv2.aruco.detectMarkers(
            gray, aruco_dict, parameters=parameters
        )

        stop = False  # 루프 탈출 플래그

        if ids is not None:
            for i in range(len(ids)):
                rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
                    corners[i], marker_length, camera_matrix, dist_coeffs
                )
                distance = np.linalg.norm(tvec)

                # 회전벡터(rvec)를 회전 행렬로 변환
                rotation_matrix, _ = cv2.Rodrigues(rvec)

                # 회전 행렬에서 회전 각도 추출
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

                # 라디안을 각도로 변환
                x_angle = np.degrees(x_angle)
                y_angle = np.degrees(y_angle)
                z_angle = np.degrees(z_angle)

                # 회전 각도 출력
                print(f"ID: {ids[i][0]} Rotation (X, Y, Z): ({x_angle:.2f}, {y_angle:.2f}, {z_angle:.2f})")

                # 마커의 경계와 축을 그립니다.
                aruco.drawDetectedMarkers(frame, corners)
                cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, 0.1)

                # 거리와 ID를 화면에 출력
                cv2.putText(
                    frame,
                    f"ID: {ids[i][0]} Distance: {distance:.3f} m",
                    (10, 30 + i * 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )

                if distance < 0.3:
                    stop = True

        cv2.imshow("frame", frame)
        if stop:
            break
    cv2.destroyAllWindows()
