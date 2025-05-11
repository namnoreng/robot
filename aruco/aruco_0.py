# Aruco 마커 생성 (체커보드 생성은 카메라 보정에서 함)

import cv2
from cv2 import aruco

# MARKER_ID = 0
MARKER_NUM = 5  # 생성할 마커의 갯수
MARKER_SIZE = 200  # pixels

# 마커 생성 시 사용할 딕셔너리 지정
marker_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)

# for 문으로 원하는 수의 마커 생성
for id in range(MARKER_NUM):
    marker_image = aruco.generateImageMarker(marker_dict, id, MARKER_SIZE)
    cv2.imshow("img", marker_image)
    cv2.imwrite(f"Image/marker_{id}.png", marker_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    # break
