import cv2
import cv2.aruco as aruco
import numpy as np
import time

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

# 마커의 실제 크기를 정확히 설정합니다 (예: 0.057미터 = 5.7cm).
marker_length = 0.0057

# AGV 제어 함수 (예시)
def control_agv(action):
    if action == "move_forward":
        print("AGV moving forward")
        # 실제 AGV 제어 코드 추가
    elif action == "turn_left":
        print("AGV turning left")
        # 실제 AGV 제어 코드 추가
    elif action == "turn_right":
        print("AGV turning right")
        # 실제 AGV 제어 코드 추가
    elif action == "stop":
        print("AGV stopping")
        # 실제 AGV 제어 코드 추가
    else:
        print("Unknown action")
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 그레이스케일로 변환합니다.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 마커 코너좌표, ID, 거부된 마커 = 마커 탐지()
    corners, ids, rejectedImgPoints = aruco.detectMarkers(
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

            # 특정 마커 ID에 따라 동작 수행
            if ids[i][0] == 0:
                control_agv("move_forward")
            elif ids[i][0] == 2:
                control_agv("turn_left")
            elif ids[i][0] == 3:
                control_agv("turn_right")
            elif ids[i][0] == 4:
                control_agv("stop")

    # 결과 프레임을 표시합니다.
    cv2.imshow("frame", frame)

    # 'q' 키를 누르면 종료합니다.
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
