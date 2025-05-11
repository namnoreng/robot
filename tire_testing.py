import cv2 as cv
import numpy as np

# Open webcam with DSHOW backend
cap1 = cv.VideoCapture(0, cv.CAP_DSHOW)
cap2 = cv.VideoCapture(1, cv.CAP_DSHOW)


# Check if webcam is opened
if not cap1.isOpened():
    print("Error: Could not open first webcam.")
    exit()

if not cap2.isOpened():
    print("Error: Could not open second webcam.")
    exit()

# Set resolution and FPS (optional)
cap1.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap1.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap1.set(cv.CAP_PROP_FPS, 30)

cap2.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap2.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap2.set(cv.CAP_PROP_FPS, 30)


print(f"Width: {cap1.get(cv.CAP_PROP_FRAME_WIDTH)}")
print(f"Height: {cap1.get(cv.CAP_PROP_FRAME_HEIGHT)}")
print(f"FPS: {cap1.get(cv.CAP_PROP_FPS)}")

print(f"Width: {cap2.get(cv.CAP_PROP_FRAME_WIDTH)}")
print(f"Height: {cap2.get(cv.CAP_PROP_FRAME_HEIGHT)}")
print(f"FPS: {cap2.get(cv.CAP_PROP_FPS)}")


while True:
    ret1, frame1 = cap1.read()
    if not ret1:
        print("Failed to capture image")
        break

    ret2, frame2 = cap2.read()
    if not ret2:
        print("Failed to capture image")
        break

    #Convert to grayscale
    gray1 = cv.cvtColor(frame1, cv.COLOR_BGR2GRAY)
    gray2 = cv.cvtColor(frame2, cv.COLOR_BGR2GRAY)

    # # Apply binary thresholding
    # _, binary1 = cv.threshold(gray1, 50, 255, cv.THRESH_BINARY)
    # _, binary2 = cv.threshold(gray2, 50, 255, cv.THRESH_BINARY)

    # Show binary image
    cv.imshow("Binary Image_1", gray1)
    cv.imshow("Binary Image_2", gray2)
    key = cv.waitKey(1)
    if key == 27:  # ESC key to exit
        break

cap1.release()
cap2.release()
cv.destroyAllWindows()
