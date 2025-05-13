import cv2 as cv
import numpy as np

# Open webcam with DSHOW backend
cap = cv.VideoCapture(0, cv.CAP_DSHOW)


# Check if webcam is opened
if not cap.isOpened():
    print("Error: Could not open first webcam.")
    exit()


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
