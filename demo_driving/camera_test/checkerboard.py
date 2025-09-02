"""
카메라 수동 캡처 프로그램 (초간소화 버전)
- 카메라 화면만 표시하고 수동으로 이미지 저장
- CSI 카메라 지원
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

def gstreamer_pipeline(capture_width=640, capture_height=480, 
                      display_width=640, display_height=480, 
                      framerate=30, flip_method=0):
    """CSI 카메라용 GStreamer 파이프라인 (csi_5x5_aruco.py 방식)"""
    return (
        f"nvarguscamerasrc sensor-id=1 ! "
        "video/x-raw(memory:NVMM), "
        f"width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        "nvvidconv flip-method=" + str(flip_method) + " ! "
        f"video/x-raw, width={display_width}, height={display_height}, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink max-buffers=1 drop=true"
    )

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
            # CSI 카메라 초기화 (csi_5x5_aruco.py 방식)
            print("[Camera] CSI 카메라 (backcam) 초기화 시도...")
            pipeline = gstreamer_pipeline(CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT, 30, 0)
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            
            if cap.isOpened():
                camera_type = "CSI (backcam)"
                print("[Camera] CSI 카메라 (backcam) 초기화 성공")
            else:
                cap = None
                # /dev/video1 (backcam)로 직접 시도
                print("[Camera] /dev/video1 (backcam)로 재시도...")
                cap = cv2.VideoCapture(1)  # /dev/video1
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, 15)  # 낮은 FPS로 설정
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기 최소화
                    
                    # 설정 후 테스트 프레임 읽기
                    import time
                    for i in range(5):  # 몇 번 시도
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            camera_type = "backcam (/dev/video1)"
                            print("[Camera] /dev/video1 (backcam) 초기화 성공")
                            break
                        time.sleep(0.1)
                    else:
                        # 테스트 프레임 읽기 실패
                        cap.release()
                        cap = None
                        print("[Camera] /dev/video1 테스트 프레임 읽기 실패")
                else:
                    cap = None
        
        if cap is None:
            # USB 카메라 (뒷카메라로 사용)
            print("[Camera] USB 카메라 (뒷카메라) 초기화 시도...")
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, 15)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # 테스트 프레임 읽기
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    camera_type = "USB (뒷카메라)"
                    print("[Camera] USB 카메라 (뒷카메라) 초기화 성공")
                else:
                    cap.release()
                    cap = None
                    print("[Camera] USB 카메라 테스트 프레임 읽기 실패")
            else:
                cap = None
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            camera_type = "USB"
            print("[Camera] USB 카메라 초기화 성공")
            
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

def main():
    """메인 함수 - 수동 캡처 전용"""
    print("=" * 60)
    print("카메라 수동 캡처 프로그램")
    print("=" * 60)
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
    print("  SPACE: 이미지 저장")
    print("  ESC/q: 종료")
    print("-" * 60)
    
    # 상태 변수
    image_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Error] 프레임 읽기 실패")
                break
            
            # 단순히 프레임 표시만
            display_frame = frame.copy()
            
            # 간단한 상태 표시
            cv2.putText(display_frame, f"Images: {image_count} | Camera: {camera_type}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display_frame, "SPACE: Save | ESC: Exit", 
                       (10, display_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # 화면 표시
            cv2.imshow('Manual Camera Capture', display_frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27 or key == ord('q'):  # ESC 또는 'q'
                break
            elif key == ord(' '):  # SPACE - 이미지 저장
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{image_count+1:03d}_{timestamp}.jpg"
                filepath = os.path.join(save_folder, filename)
                cv2.imwrite(filepath, frame)
                image_count += 1
                print(f"[Save] 이미지 저장: {filename}")
    
    except KeyboardInterrupt:
        print("\n[Exit] 키보드 인터럽트로 종료합니다.")
    except Exception as e:
        print(f"[Error] 오류 발생: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"\n[Summary] 프로그램 종료")
        print(f"[Summary] 총 저장된 이미지: {image_count}장")
        print(f"[Summary] 저장 위치: {save_folder}")

if __name__ == "__main__":
    main()
