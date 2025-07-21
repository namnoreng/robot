import cv2 as cv
from cv2 import aruco
import numpy as np

# OpenCV 버전에 따라 lineType 설정
cv_version = cv.__version__.split(".")
use_line_aa = int(cv_version[0]) >= 4 or (int(cv_version[0]) == 3 and int(cv_version[1]) >= 4)

def start_detecting_aruco(cap, marker_dict, param_markers):
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture image")
            break

        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        marker_corners, marker_IDs, reject = aruco.detectMarkers(
            gray_frame, marker_dict, parameters=param_markers
        )

        if marker_corners:
            for ids, corners in zip(marker_IDs, marker_corners):
                # LINE_AA는 OpenCV 3.4 이상부터 지원되므로 조건 처리
                line_type = cv.LINE_AA if use_line_aa else 8
                cv.polylines(
                    frame, [corners.astype(np.int32)], True, (0, 255, 255), 4, line_type
                )
                corners = corners.reshape(4, 2)
                corners = corners.astype(int)
                top_right = corners[0].ravel()
                top_left = corners[1].ravel()
                bottom_right = corners[2].ravel()
                bottom_left = corners[3].ravel()
                cv.putText(
                    frame,
                    f"id: {ids[0]}",
                    tuple(top_right),
                    cv.FONT_HERSHEY_PLAIN,
                    1.3,
                    (200, 100, 0),
                    2,
                    line_type,
                )
        #cv.imshow("frame", frame)
        key = cv.waitKey(1)
        if key == ord("q"):
            break

    cv.destroyAllWindows()
