# 아루코 마커를 생성하는 코드이다.
# 마커에 ID 와 저오를  출력하는 코드이다.

import cv2
import cv2.aruco as aruco

# 마커 사전 가져오기
marker_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)

# 마커 ID와 관련된 정보 설정
marker_info = {
    0: "station A",
    1: "station B",
    2: "station C",
}

# 마커 생성 및 저장
for marker_id, info in marker_info.items():
    marker_image = aruco.generateImageMarker(marker_dict, marker_id, 200)
    cv2.putText(
        marker_image,
        f"id: {marker_id}, info: {info}",
        (10, 190),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )
    cv2.imwrite(f"aruco_marker_{marker_id}.png", marker_image)
