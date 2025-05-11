import cv2 as cv
from cv2 import aruco
import numpy as np
import serial

# 🔌 시리얼 포트 설정 (본인 환경에 맞게 수정)
ser = serial.Serial('COM3', 9600)  # Windows: COMx / Linux: '/dev/ttyUSB0'

# 마커 딕셔너리 지정
marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
param_markers = aruco.DetectorParameters()

# 웹캠 설정
cap = cv.VideoCapture(0)
cap.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv.CAP_PROP_FPS, 30)

# 이전에 보낸 마커 ID 저장 (중복 방지용)
sent_ids = set()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    marker_corners, marker_IDs, reject = aruco.detectMarkers(
        gray_frame, marker_dict, parameters=param_markers
    )

    if marker_IDs is not None:
        for ids, corners in zip(marker_IDs, marker_corners):
            marker_id = ids[0]

            cv.polylines(
                frame, [corners.astype(np.int32)], True, (0, 255, 255), 4, cv.LINE_AA
            )

            corners = corners.reshape(4, 2).astype(int)
            top_right = corners[0].ravel()

            cv.putText(
                frame,
                f"id: {marker_id}",
                top_right,
                cv.FONT_HERSHEY_PLAIN,
                1.3,
                (200, 100, 0),
                2,
                cv.LINE_AA,
            )

            # 시리얼 전송 메시지 설정
            if marker_id == 1:
                message = "Forward\n"
            elif marker_id == 2:
                message = "Backward\n"
            elif marker_id == 3:
                message = "Turn Left\n"
            elif marker_id == 4:
                message = "Turn Right\n"
            else:
                message = f"Unknown ID {marker_id}\n"

            # 중복 전송 방지: 한 프레임에 동일한 ID는 한 번만 전송
            if marker_id not in sent_ids:
                ser.write(message.encode())
                print(f"[Sent to Serial] {message.strip()}")
                sent_ids.add(marker_id)

    else:
        # 마커가 모두 사라졌으면, 전송 기록 초기화
        sent_ids.clear()

    cv.imshow("frame", frame)

    key = cv.waitKey(1)
    if key == ord("q"):
        break

cap.release()
cv.destroyAllWindows()
