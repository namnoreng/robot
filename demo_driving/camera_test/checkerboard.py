"""
체커보드 촬영 및 카메라 캘리브레이션용 이미지 수집 프로그램
- 체커보드를 인식하여 자동/수동으로 캘리브레이션 이미지 저장
- CSI 카메라와 USB 카메라 지원
- 실시간 체커보드 코너 검출 및 시각화
"""

import cv2
import numpy as np
import os
import time
import platform
from datetime import datetime

# 설정값
CHECKERBOARD_SIZE = (7, 6)  # 체커보드 내부 코너 개수 (가로, 세로)
SQUARE_SIZE = 20.0  # 체커보드 한 칸의 실제 크기 (mm)

# 카메라 해상도 설정
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# 저장 설정
SAVE_FOLDER = "checkerboard_images_back"
MIN_DETECTION_INTERVAL = 2.0  # 자동 저장 최소 간격 (초)

def create_save_folder():
    """저장 폴더 생성"""
    if not os.path.exists(SAVE_FOLDER):
        os.makedirs(SAVE_FOLDER)
        print(f"[Setup] 저장 폴더 생성: {SAVE_FOLDER}")
    return SAVE_FOLDER

def initialize_camera():
    """카메라 초기화 (CSI 우선, USB 백업)"""
    current_platform = platform.system()
    cap = None
    camera_type = "Unknown"
    
    try:
        if current_platform == "Linux":
            # Jetson Nano CSI 카메라 시도
            print("[Camera] CSI 카메라 초기화 시도...")
            gst_pipeline = (
                f"nvarguscamerasrc ! "
                f"video/x-raw(memory:NVMM), width={CAMERA_WIDTH}, height={CAMERA_HEIGHT}, "
                f"format=NV12, framerate={CAMERA_FPS}/1 ! "
                f"nvvidconv ! "
                f"video/x-raw, format=BGR ! "
                f"appsink"
            )
            cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                camera_type = "CSI"
                print("[Camera] CSI 카메라 초기화 성공")
            else:
                cap = None
        
        if cap is None:
            # USB 카메라 (뒷카메라로 사용)
            print("[Camera] USB 카메라 (뒷카메라) 초기화 시도...")
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            camera_type = "USB (뒷카메라)"
            print("[Camera] USB 카메라 (뒷카메라) 초기화 성공")
            
    except Exception as e:
        print(f"[Camera] 카메라 초기화 실패: {e}")
        return None, "Failed"
    
    if cap is None or not cap.isOpened():
        print("[Camera] 카메라를 열 수 없습니다.")
        return None, "Failed"
    
    # 카메라 정보 확인
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"[Camera] {camera_type} 카메라 설정 완료")
    print(f"[Camera] 해상도: {actual_width}x{actual_height}, FPS: {actual_fps:.1f}")
    
    return cap, camera_type

def detect_checkerboard(frame, checkerboard_size):
    """
    체커보드 코너 검출
    
    Args:
        frame: 입력 이미지
        checkerboard_size: 체커보드 내부 코너 개수 (가로, 세로)
    
    Returns:
        success: 검출 성공 여부
        corners: 검출된 코너 좌표
        frame_with_corners: 코너가 그려진 이미지
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 체커보드 코너 검출
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    
    # 코너 검출
    ret, corners = cv2.findChessboardCorners(gray, checkerboard_size, None)
    
    frame_with_corners = frame.copy()
    
    if ret:
        # 서브픽셀 정확도로 코너 위치 개선
        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        
        # 코너 그리기
        cv2.drawChessboardCorners(frame_with_corners, checkerboard_size, corners_refined, ret)
        
        # 코너 개수 표시
        corner_count = len(corners_refined)
        cv2.putText(frame_with_corners, f"Corners: {corner_count}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 상태 표시
        cv2.putText(frame_with_corners, "CHECKERBOARD DETECTED!", 
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return True, corners_refined, frame_with_corners
    else:
        # 검출 실패 상태 표시
        cv2.putText(frame_with_corners, "Searching for checkerboard...", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(frame_with_corners, f"Pattern: {checkerboard_size[0]}x{checkerboard_size[1]} corners", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        return False, None, frame_with_corners

def save_image(frame, corners, image_count, save_folder):
    """
    체커보드 이미지 저장
    
    Args:
        frame: 저장할 이미지
        corners: 검출된 코너
        image_count: 이미지 번호
        save_folder: 저장 폴더
    
    Returns:
        filename: 저장된 파일명
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"checkerboard_{image_count:03d}_{timestamp}.jpg"
    filepath = os.path.join(save_folder, filename)
    
    # 이미지 저장
    cv2.imwrite(filepath, frame)
    
    # 코너 데이터 저장 (선택사항)
    corner_filename = f"corners_{image_count:03d}_{timestamp}.npy"
    corner_filepath = os.path.join(save_folder, corner_filename)
    np.save(corner_filepath, corners)
    
    print(f"[Save] 이미지 저장: {filename} (코너: {len(corners)}개)")
    return filename

def calculate_reprojection_error(objpoints, imgpoints, camera_matrix, dist_coeffs, rvecs, tvecs):
    """재투영 오차 계산"""
    total_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        total_error += error
    return total_error / len(objpoints)

def quick_calibration(save_folder, checkerboard_size, square_size):
    """
    저장된 이미지들로 간단한 캘리브레이션 수행
    
    Args:
        save_folder: 이미지가 저장된 폴더
        checkerboard_size: 체커보드 크기
        square_size: 체커보드 한 칸의 실제 크기 (mm)
    """
    print(f"\n[Calibration] 간단한 캘리브레이션 수행...")
    
    # 3D 객체 포인트 준비
    objp = np.zeros((checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:checkerboard_size[0], 0:checkerboard_size[1]].T.reshape(-1, 2)
    objp *= square_size
    
    objpoints = []  # 3D 포인트
    imgpoints = []  # 2D 포인트_
    
    # 저장된 이미지 파일 찾기
    image_files = [f for f in os.listdir(save_folder) if f.startswith('checkerboard_') and f.endswith('.jpg')]
    
    if len(image_files) < 3:
        print(f"[Calibration] 캘리브레이션을 위한 이미지가 부족합니다. (현재: {len(image_files)}개, 최소: 3개)")
        return None
    
    print(f"[Calibration] {len(image_files)}개 이미지로 캘리브레이션 시작...")
    
    valid_images = 0
    for filename in image_files:
        filepath = os.path.join(save_folder, filename)
        img = cv2.imread(filepath)
        if img is None:
            continue
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, checkerboard_size, None)
        
        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
            objpoints.append(objp)
            imgpoints.append(corners_refined)
            valid_images += 1
    
    if valid_images < 3:
        print(f"[Calibration] 유효한 이미지가 부족합니다. (유효: {valid_images}개)")
        return None
    
    # 카메라 캘리브레이션 실행
    img_shape = gray.shape[::-1]
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, img_shape, None, None
    )
    
    if ret:
        # 재투영 오차 계산
        reprojection_error = calculate_reprojection_error(objpoints, imgpoints, camera_matrix, dist_coeffs, rvecs, tvecs)
        
        print(f"[Calibration] 캘리브레이션 완료!")
        print(f"[Calibration] 사용된 이미지: {valid_images}개")
        print(f"[Calibration] 재투영 오차: {reprojection_error:.3f} 픽셀")
        print(f"[Calibration] 카메라 매트릭스:")
        print(camera_matrix)
        print(f"[Calibration] 왜곡 계수:")
        print(dist_coeffs.flatten())
        
        # 결과 저장
        calib_folder = os.path.join(save_folder, "calibration_result")
        if not os.path.exists(calib_folder):
            os.makedirs(calib_folder)
            
        np.save(os.path.join(calib_folder, "camera_matrix.npy"), camera_matrix)
        np.save(os.path.join(calib_folder, "dist_coeffs.npy"), dist_coeffs)
        
        # 결과 텍스트 파일 저장
        with open(os.path.join(calib_folder, "calibration_info.txt"), 'w') as f:
            f.write(f"Camera Calibration Results\n")
            f.write(f"========================\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Images used: {valid_images}\n")
            f.write(f"Reprojection error: {reprojection_error:.6f} pixels\n")
            f.write(f"Checkerboard size: {checkerboard_size[0]}x{checkerboard_size[1]}\n")
            f.write(f"Square size: {square_size} mm\n\n")
            f.write(f"Camera Matrix:\n{camera_matrix}\n\n")
            f.write(f"Distortion Coefficients:\n{dist_coeffs.flatten()}\n")
        
        print(f"[Calibration] 결과 저장됨: {calib_folder}")
        return camera_matrix, dist_coeffs
    else:
        print(f"[Calibration] 캘리브레이션 실패")
        return None

def main():
    """메인 함수"""
    print("=" * 60)
    print("체커보드 촬영 및 카메라 캘리브레이션 프로그램")
    print("=" * 60)
    print(f"체커보드 설정: {CHECKERBOARD_SIZE[0]}x{CHECKERBOARD_SIZE[1]} 내부 코너")
    print(f"체커보드 한 칸 크기: {SQUARE_SIZE}mm")
    print(f"카메라 해상도: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print()
    
    # 저장 폴더 생성
    save_folder = create_save_folder()
    
    # 카메라 초기화
    cap, camera_type = initialize_camera()
    if cap is None:
        print("[Error] 카메라 초기화 실패")
        return
    
    print("\n조작법:")
    print("  SPACE: 수동으로 이미지 저장")
    print("  'a': 자동 저장 모드 토글")
    print("  'c': 간단한 캘리브레이션 수행")
    print("  'r': 통계 리셋")
    print("  's': 스크린샷 저장")
    print("  ESC/q: 종료")
    print("-" * 60)
    
    # 상태 변수
    image_count = 0
    auto_save = False
    last_save_time = 0
    detection_count = 0
    total_frames = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Error] 프레임 읽기 실패")
                break
            
            total_frames += 1
            
            # 체커보드 검출
            detected, corners, display_frame = detect_checkerboard(frame, CHECKERBOARD_SIZE)
            
            if detected:
                detection_count += 1
                
                # 자동 저장 모드
                current_time = time.time()
                if auto_save and (current_time - last_save_time) >= MIN_DETECTION_INTERVAL:
                    save_image(frame, corners, image_count + 1, save_folder)
                    image_count += 1
                    last_save_time = current_time
            
            # 상태 정보 표시
            detection_rate = (detection_count / total_frames * 100) if total_frames > 0 else 0
            
            # 상태 바 그리기
            status_y = display_frame.shape[0] - 80
            cv2.rectangle(display_frame, (0, status_y), (display_frame.shape[1], display_frame.shape[0]), (50, 50, 50), -1)
            
            status_text = [
                f"Camera: {camera_type} | Images: {image_count} | Detection: {detection_rate:.1f}%",
                f"Auto-save: {'ON' if auto_save else 'OFF'} | Pattern: {CHECKERBOARD_SIZE[0]}x{CHECKERBOARD_SIZE[1]}",
                "SPACE:Save | A:Auto | C:Calibrate | R:Reset | S:Screenshot | ESC:Exit"
            ]
            
            for i, text in enumerate(status_text):
                cv2.putText(display_frame, text, (10, status_y + 20 + i*15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 화면 표시
            cv2.imshow('Checkerboard Capture', display_frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27 or key == ord('q'):  # ESC 또는 'q'
                break
            elif key == ord(' '):  # SPACE - 수동 저장
                if detected:
                    save_image(frame, corners, image_count + 1, save_folder)
                    image_count += 1
                    last_save_time = time.time()
                else:
                    print("[Warning] 체커보드가 검출되지 않아 저장하지 않습니다.")
            elif key == ord('a'):  # 자동 저장 토글
                auto_save = not auto_save
                print(f"[Mode] 자동 저장: {'활성화' if auto_save else '비활성화'}")
            elif key == ord('c'):  # 캘리브레이션 수행
                if image_count >= 3:
                    result = quick_calibration(save_folder, CHECKERBOARD_SIZE, SQUARE_SIZE)
                    if result is not None:
                        print("[Success] 캘리브레이션 완료!")
                    else:
                        print("[Error] 캘리브레이션 실패")
                else:
                    print(f"[Warning] 캘리브레이션을 위해 최소 3장의 이미지가 필요합니다. (현재: {image_count}장)")
            elif key == ord('r'):  # 통계 리셋
                detection_count = 0
                total_frames = 0
                print("[Reset] 통계가 리셋되었습니다.")
            elif key == ord('s'):  # 스크린샷
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_name = f"screenshot_{timestamp}.jpg"
                cv2.imwrite(os.path.join(save_folder, screenshot_name), display_frame)
                print(f"[Screenshot] 저장됨: {screenshot_name}")
    
    except KeyboardInterrupt:
        print("\n[Exit] 키보드 인터럽트로 종료합니다.")
    except Exception as e:
        print(f"[Error] 오류 발생: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"\n[Summary] 프로그램 종료")
        print(f"[Summary] 총 저장된 이미지: {image_count}장")
        print(f"[Summary] 검출률: {(detection_count / total_frames * 100) if total_frames > 0 else 0:.1f}%")
        print(f"[Summary] 저장 위치: {save_folder}")

if __name__ == "__main__":
    main()
