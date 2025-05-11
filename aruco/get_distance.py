import cv2
import cv2.aruco as aruco
import numpy as np

# 보정 행렬과 왜곡 계수를 불러옵니다.
camera_matrix = np.load(r"Image/camera_matrix.npy")
dist_coeffs = np.load(r"Image/dist_coeffs.npy")

print("Loaded camera matrix : \n", camera_matrix)
print("Loaded distortion coefficients : \n", dist_coeffs)

# 3D 측정에 사용할 Aruco 마커 딕셔너리를 선택합니다.
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
parameters = aruco.DetectorParameters()

# 비디오 캡처를 시작합니다.
# cap = cv2.VideoCapture(0)
cap = cv2.VideoCapture(0)

# 마커의 실제 크기를 정확히 설정합니다 (예: 0.08미터 = 8cm).
# marker_length = 0.08  # 마커의 실제 크기 (미터 단위)
marker_length = 0.05 / 2.54  # 마커의 실제 크기 (미터 단위)

while True:
    ret, frame = cap.read()
    if not ret:
        break

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

            # 길이가 0.1인 축을 그림 (dist_coeffs: 왜곡 계수. 카메라 왜곡 보정용)
            cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, 0.1)

            # 거리를 화면에 출력합니다.
            # distance의 소수점 3자리까지 값 미터, 텍스트 위치, 텍스트 크기 1, 초록, 텍스트 선 두께 2
            cv2.putText(
                frame,
                f"ID: {ids[i][0]} Distance: {distance:.3f} m",
                (10, 30 + i * 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                # cv2.FONT_HERSHEY_PLAIN,
                1,
                (0, 255, 0),
                2,
            )
            # cv2.putText(
            #     frame,
            #     f"tvec: {tvec}",
            #     (10, 70 + i * 30),
            #     cv2.FONT_HERSHEY_SIMPLEX,
            #     1,
            #     (0, 0, 255),
            #     2,
            # )

    # 결과 프레임을 표시합니다.
    cv2.imshow("frame", frame)

    # 'q' 키를 누르면 종료합니다.
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
