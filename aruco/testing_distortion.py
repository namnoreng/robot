import numpy as np
import cv2 as cv
import glob

# termination criteria
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(5,4,0)
objp = np.zeros((6*5, 3), np.float32)  # 6x5 체스보드
objp[:, :2] = np.mgrid[0:5, 0:6].T.reshape(-1, 2)

# Arrays to store object points and image points from all the images.
objpoints = []  # 3d point in real world space
imgpoints = []  # 2d points in image plane.

images = glob.glob(r"Image_back/*.jpg")

for fname in images:
    img = cv.imread(fname)
    if img is None:
        print(f"Error: Unable to read image {fname}")
        continue

    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # Find the chess board corners
    ret, corners = cv.findChessboardCorners(gray, (5, 6), None)

    # If found, add object points, image points (after refining them)
    if ret:
        objpoints.append(objp)

        corners2 = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

        # Draw and display the corners
        cv.drawChessboardCorners(img, (5, 6), corners2, ret)
        cv.imshow('img', img)
        cv.waitKey(500)
    else:
        print(f"Chessboard corners not found in image {fname}")

cv.destroyAllWindows()