import cv2
import cv2.aruco as aruco
import numpy as np
from pymycobot.myagv import MyAgv
import time

# AGV 제어를 위한 객체 생성
agv = MyAgv("/dev/ttyAMA2", 115200)

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
marker_length = 0.04  # 마커의 실제 크기 (미터 단위)

# AGV 제어 함수
def control_agv_based_on_marker(id, distance):
    """
    Aruco 마커 ID와 거리에 따라 AGV를 제어합니다.
    """
    if distance <= 0.3:
        if id in [1, 5]:
            # ID 1, 5: AGV 정지
            print(f"ID {id} 감지됨 - AGV 정지")
            agv.stop()
        elif id in [2, 4]:
            # ID 2, 4: AGV 전진
            print(f"ID {id} 감지됨 - AGV 전진")
            agv.go_ahead(50, 1)  # 속도 50으로 1초간 전진
    else: id == 3
        # ID 3: AGV 정지
    print("ID 3 감지됨 - AGV 정지")
    agv.stop()

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

    # 결과 프레임을 표시합니다.
    cv2.imshow("frame", frame)

    # 'q' 키를 누르면 종료합니다.
    if cv2.waitKey(1) & 0xFF == ord("q"):
        agv.stop()  # 종료 시 AGV 정지
        break

cap.release()
cv2.destroyAllWindows()
