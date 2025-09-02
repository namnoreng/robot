#!/usr/bin/env python3
"""
체커보드 이미지들로부터 카메라 캘리브레이션 수행
저장된 체커보드 이미지들을 분석하여 카메라 매트릭스와 왜곡계수 계산
"""

import cv2
import numpy as np
import os
import glob
from datetime import datetime

# 체커보드 설정 (checkerboard.py와 동일하게 설정)
CHECKERBOARD_SIZE = (6, 5)  # 내부 코너 개수 (가로, 세로)
SQUARE_SIZE = 20.0  # 체커보드 한 칸의 실제 크기 (mm)

def calibrate_camera_from_images(image_folder, checkerboard_size, square_size):
    """
    저장된 체커보드 이미지들로부터 카메라 캘리브레이션 수행
    
    Args:
        image_folder: 체커보드 이미지가 저장된 폴더
        checkerboard_size: 체커보드 내부 코너 개수 (가로, 세로)
        square_size: 체커보드 한 칸의 실제 크기 (mm)
    
    Returns:
        camera_matrix: 카메라 매트릭스
        dist_coeffs: 왜곡 계수
        reprojection_error: 재투영 오차
        valid_images: 사용된 유효 이미지 수
    """
    print(f"📐 체커보드 캘리브레이션 시작...")
    print(f"📁 이미지 폴더: {image_folder}")
    print(f"📏 체커보드 설정: {checkerboard_size[0]}x{checkerboard_size[1]} 코너, {square_size}mm 격자")
    print("=" * 60)
    
    # 3D 객체 포인트 준비 (실제 체커보드 좌표)
    objp = np.zeros((checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:checkerboard_size[0], 0:checkerboard_size[1]].T.reshape(-1, 2)
    objp *= square_size  # mm 단위로 스케일링
    
    # 3D와 2D 포인트 저장 배열
    objpoints = []  # 3D 포인트 (실제 세계 좌표)
    imgpoints = []  # 2D 포인트 (이미지 픽셀 좌표)
    
    # 이미지 파일들 찾기
    image_pattern = os.path.join(image_folder, "capture_*.jpg")
    image_files = glob.glob(image_pattern)
    
    if not image_files:
        print(f"❌ 오류: {image_folder}에서 체커보드 이미지를 찾을 수 없습니다.")
        return None
    
    print(f"🔍 발견된 이미지 파일: {len(image_files)}개")
    print("-" * 60)
    
    # 체커보드 검출 기준
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    
    valid_images = 0
    failed_images = []
    
    for i, image_path in enumerate(sorted(image_files)):
        filename = os.path.basename(image_path)
        print(f"[{i+1:2d}/{len(image_files)}] 처리 중: {filename}", end=" ... ")
        
        # 이미지 읽기
        img = cv2.imread(image_path)
        if img is None:
            print("❌ 이미지 읽기 실패")
            failed_images.append(filename)
            continue
        
        # 그레이스케일 변환
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 체커보드 코너 검출
        ret, corners = cv2.findChessboardCorners(gray, checkerboard_size, None)
        
        if ret:
            # 서브픽셀 정확도로 코너 위치 개선
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
            # 3D-2D 포인트 쌍 저장
            objpoints.append(objp)
            imgpoints.append(corners_refined)
            
            valid_images += 1
            print("✅ 성공")
            
            # 첫 번째와 마지막 이미지는 결과 표시 (선택사항)
            if i == 0 or i == len(image_files) - 1:
                img_with_corners = img.copy()
                cv2.drawChessboardCorners(img_with_corners, checkerboard_size, corners_refined, ret)
                
                # 결과 이미지 저장
                result_path = os.path.join(image_folder, f"detected_{filename}")
                cv2.imwrite(result_path, img_with_corners)
                
        else:
            print("❌ 체커보드 검출 실패")
            failed_images.append(filename)
    
    print("-" * 60)
    print(f"📊 검출 결과:")
    print(f"   ✅ 성공: {valid_images}개")
    print(f"   ❌ 실패: {len(failed_images)}개")
    
    if failed_images:
        print(f"   실패한 이미지들: {', '.join(failed_images[:5])}")
        if len(failed_images) > 5:
            print(f"   ... 외 {len(failed_images) - 5}개")
    
    # 캘리브레이션 수행
    if valid_images < 3:
        print(f"❌ 오류: 유효한 이미지가 부족합니다. (최소 3개 필요, 현재 {valid_images}개)")
        return None
    
    print(f"\n🔧 카메라 캘리브레이션 수행 중... ({valid_images}개 이미지 사용)")
    
    # 이미지 크기 (첫 번째 유효 이미지에서 가져오기)
    img_shape = gray.shape[::-1]
    
    # 카메라 캘리브레이션 실행
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, img_shape, None, None
    )
    
    if not ret:
        print("❌ 오류: 캘리브레이션이 실패했습니다.")
        return None
    
    # 재투영 오차 계산
    total_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        total_error += error
    
    reprojection_error = total_error / len(objpoints)
    
    return camera_matrix, dist_coeffs, reprojection_error, valid_images

def save_calibration_results(camera_matrix, dist_coeffs, reprojection_error, valid_images, 
                           checkerboard_size, square_size, output_folder):
    """
    캘리브레이션 결과를 파일로 저장
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # NumPy 배열로 저장 (.npy 파일)
    camera_matrix_path = os.path.join(output_folder, "camera_matrix.npy")
    dist_coeffs_path = os.path.join(output_folder, "dist_coeffs.npy")
    
    np.save(camera_matrix_path, camera_matrix)
    np.save(dist_coeffs_path, dist_coeffs)
    
    # 텍스트 파일로도 저장
    info_path = os.path.join(output_folder, "calibration_info.txt")
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write("카메라 캘리브레이션 결과\n")
        f.write("=" * 40 + "\n")
        f.write(f"날짜: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"사용된 이미지: {valid_images}개\n")
        f.write(f"재투영 오차: {reprojection_error:.6f} 픽셀\n")
        f.write(f"체커보드 크기: {checkerboard_size[0]}x{checkerboard_size[1]} 코너\n")
        f.write(f"격자 크기: {square_size} mm\n\n")
        
        f.write("카메라 매트릭스 (Camera Matrix):\n")
        f.write("fx   0   cx\n")
        f.write(" 0  fy   cy\n")
        f.write(" 0   0    1\n\n")
        f.write(f"fx (초점거리 X): {camera_matrix[0, 0]:.2f}\n")
        f.write(f"fy (초점거리 Y): {camera_matrix[1, 1]:.2f}\n")
        f.write(f"cx (주점 X):     {camera_matrix[0, 2]:.2f}\n")
        f.write(f"cy (주점 Y):     {camera_matrix[1, 2]:.2f}\n\n")
        
        f.write("카메라 매트릭스 (전체):\n")
        for row in camera_matrix:
            f.write(f"[{row[0]:10.4f} {row[1]:10.4f} {row[2]:10.4f}]\n")
        
        f.write(f"\n왜곡 계수 (Distortion Coefficients):\n")
        f.write(f"k1 (방사 왜곡 1): {dist_coeffs[0, 0]:.6f}\n")
        f.write(f"k2 (방사 왜곡 2): {dist_coeffs[0, 1]:.6f}\n")
        f.write(f"p1 (접선 왜곡 1): {dist_coeffs[0, 2]:.6f}\n")
        f.write(f"p2 (접선 왜곡 2): {dist_coeffs[0, 3]:.6f}\n")
        f.write(f"k3 (방사 왜곡 3): {dist_coeffs[0, 4]:.6f}\n\n")
        
        f.write("왜곡 계수 (전체):\n")
        f.write(f"[{' '.join([f'{x:.6f}' for x in dist_coeffs.flatten()])}]\n")
    
    print(f"💾 결과 저장 완료:")
    print(f"   📄 카메라 매트릭스: {camera_matrix_path}")
    print(f"   📄 왜곡 계수: {dist_coeffs_path}")
    print(f"   📄 상세 정보: {info_path}")

def main():
    """메인 함수"""
    print("🎯 체커보드 이미지 캘리브레이션 프로그램")
    print("=" * 60)
    
    # 이미지 폴더 경로
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_folder = os.path.join(script_dir, "checkerboard_images_back")
    output_folder = os.path.join(script_dir, "calibration_result")
    
    if not os.path.exists(image_folder):
        print(f"❌ 오류: 이미지 폴더를 찾을 수 없습니다: {image_folder}")
        return
    
    # 캘리브레이션 수행
    result = calibrate_camera_from_images(image_folder, CHECKERBOARD_SIZE, SQUARE_SIZE)
    
    if result is None:
        print("❌ 캘리브레이션이 실패했습니다.")
        return
    
    camera_matrix, dist_coeffs, reprojection_error, valid_images = result
    
    # 결과 출력
    print("\n🎉 캘리브레이션 완료!")
    print("=" * 60)
    print(f"📊 사용된 이미지: {valid_images}개")
    print(f"📏 재투영 오차: {reprojection_error:.3f} 픽셀")
    print(f"📐 카메라 매트릭스:")
    print(camera_matrix)
    print(f"🔧 왜곡 계수:")
    print(dist_coeffs.flatten())
    
    # 오차 평가
    if reprojection_error < 0.5:
        print("✅ 매우 좋은 캘리브레이션 결과입니다!")
    elif reprojection_error < 1.0:
        print("👍 좋은 캘리브레이션 결과입니다.")
    elif reprojection_error < 2.0:
        print("⚠️  보통 수준의 캘리브레이션 결과입니다.")
    else:
        print("❌ 캘리브레이션 품질이 낮습니다. 더 많은 이미지나 다양한 각도가 필요할 수 있습니다.")
    
    # 결과 저장
    save_calibration_results(camera_matrix, dist_coeffs, reprojection_error, valid_images,
                           CHECKERBOARD_SIZE, SQUARE_SIZE, output_folder)
    
    print(f"\n📁 결과는 다음 폴더에 저장되었습니다: {output_folder}")
    print("🎯 ArUco 마커 거리 측정 등에 사용할 수 있습니다!")

if __name__ == "__main__":
    main()
