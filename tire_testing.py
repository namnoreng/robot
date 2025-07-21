import cv2 as cv
import platform

# 운영체제 확인
system_platform = platform.system()

if system_platform == 'Windows':
    cap = cv.VideoCapture(0, cv.CAP_DSHOW)  # Windows는 DirectShow 사용
elif system_platform == 'Linux':
    cap = cv.VideoCapture(0)               # Linux는 백엔드 지정 없이 사용
else:
    raise RuntimeError(f"{system_platform} 운영체제는 지원하지 않습니다.")

# 카메라 확인
if not cap.isOpened():
    print("카메라를 열 수 없습니다.")
else:
    print(f"{system_platform} 환경에서 카메라 열기 성공")



# Set resolution and FPS (optional)
cap.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv.CAP_PROP_FPS, 30)


print(f"Width: {cap.get(cv.CAP_PROP_FRAME_WIDTH)}")
print(f"Height: {cap.get(cv.CAP_PROP_FRAME_HEIGHT)}")
print(f"FPS: {cap.get(cv.CAP_PROP_FPS)}")


while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture image")
        break

    #Convert to grayscale
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    # Apply binary thresholding
    _, binary = cv.threshold(gray, 50, 255, cv.THRESH_BINARY)

    # Show binary image
    cv.imshow("original",frame)
    cv.imshow("Binary Image", binary)
    key = cv.waitKey(1)
    if key == 27:  # ESC key to exit
        break

cap.release()
cv.destroyAllWindows()
