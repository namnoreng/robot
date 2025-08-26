import cv2

# GStreamer 파이프라인 (해상도/프레임레이트 조정 가능)
def gstreamer_pipeline(
    capture_width=1280,
    capture_height=720,
    display_width=1280,
    display_height=720,
    framerate=30,
    flip_method=0,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        f"width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        "nvvidconv flip-method=" + str(flip_method) + " ! "
        f"video/x-raw, width={display_width}, height={display_height}, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink"
    )

cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("카메라 열기 실패")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 🎯 여기서 영상처리 테스트 가능
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)   # 흑백 변환
    edges = cv2.Canny(gray, 100, 200)                # 엣지 검출

    # 화면 표시
    cv2.imshow("CSI Camera - Original", frame)
    cv2.imshow("CSI Camera - Edges", edges)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC 종료
        break

cap.release()
cv2.destroyAllWindows()
