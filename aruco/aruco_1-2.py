# 해당 카메라로 실제 찍은 체커보드 이미지를 활용한 보정
import cv2
import numpy as np
import os
import glob

# 체스보드 패턴의 내부 코너 수를 설정합니다.
CHECKERBOARD = (6, 5)
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# 3D 점과 2D 점을 저장할 배열을 초기화합니다.
objpoints = []  # 3D 점 (체스보드의 실제 크기 좌표)
imgpoints = []  # 2D 점 (이미지 내의 좌표)

# 체스보드의 3D 점들을 초기화합니다.
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0 : CHECKERBOARD[0], 0 : CHECKERBOARD[1]].T.reshape(-1, 2)
# objp *= 15  # 각 체스보드 셀의 크기가 15mm
objp *= 15  # 각 체스보드 셀의 크기가 15mm 

# 체스보드 이미지들을 읽어옵니다.
image_paths = glob.glob(r"Image/6x5/*.jpg")  # 이미지 파일 경로를 설정합니다.

print(f"Found {len(image_paths)} images")

for fname in image_paths:
    img = cv2.imread(fname)
    if img is None:
        print(f"Failed to load image {fname}")
        continue

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 이미지 대비 조정
    gray = cv2.equalizeHist(gray)

    # 체스보드 코너 찾기
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)

    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

        img = cv2.drawChessboardCorners(img, CHECKERBOARD, corners2, ret)
        cv2.imshow("img", img)
        cv2.waitKey(0)  # 사용자가 키를 누를 때까지 기다립니다.
    else:
        print(f"Chessboard corners not found in image {fname}")

cv2.destroyAllWindows()

if len(objpoints) == 0 or len(imgpoints) == 0:
    print("No chessboard corners were found in any image. Exiting.")
    exit()

# 카메라 보정을 수행합니다.
ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

# 결과를 출력합니다.
print("Camera matrix : \n", camera_matrix)
print("Distortion coefficients : \n", dist_coeffs)

# 보정된 행렬과 왜곡 계수를 저장합니다.
np.save(r"Image/camera_matrix.npy", camera_matrix)
np.save(r"Image/dist_coeffs.npy", dist_coeffs)
