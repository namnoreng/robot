#!/usr/bin/env python3
"""
캘리브레이션 결과 테스트 프로그램
저장된 camera_matrix.npy와 dist_coeffs.npy를 사용하여 실시간 왜곡 보정 화면 표시
"""

import cv2
import numpy as np
import os

def gstreamer_pipeline(camera_device="/dev/frontcam"):
    """CSI 카메라용 GStreamer 파이프라인"""
    return (
        f"nvarguscamerasrc sensor-id=0 ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)640, height=(int)480, "
        "format=(string)NV12, framerate=(fraction)30/1 ! "
        "nvvidconv flip-method=2 ! "
        "video/x-raw, width=(int)640, height=(int)480, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
    )

def v4l2_pipeline(camera_device="/dev/frontcam"):
    """V4L2 카메라용 파이프라인 (심볼릭 링크 사용)"""
    return (
        f"v4l2src device={camera_device} ! "
        "video/x-raw, width=640, height=480, framerate=30/1 ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink"
    )

def load_calibration_data(camera_type="front"):
    """캘리브레이션 데이터 로드"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 현재 테스트용 캘리브레이션 결과만 사용
    calibration_dir = os.path.join(script_dir, "calibration_result")
    
    if camera_type == "front":
        camera_matrix_path = os.path.join(calibration_dir, "camera_front_matrix.npy")
        dist_coeffs_path = os.path.join(calibration_dir, "dist_front_coeffs.npy")
    elif camera_type == "back":
        camera_matrix_path = os.path.join(calibration_dir, "camera_back_matrix.npy")
        dist_coeffs_path = os.path.join(calibration_dir, "dist_back_coeffs.npy")
    else:  # csi 또는 default - 기본적으로 front 사용
        camera_matrix_path = os.path.join(calibration_dir, "camera_front_matrix.npy")
        dist_coeffs_path = os.path.join(calibration_dir, "dist_front_coeffs.npy")
    
    if not os.path.exists(camera_matrix_path) or not os.path.exists(dist_coeffs_path):
        print("❌ 캘리브레이션 파일을 찾을 수 없습니다!")
        print(f"   경로 확인: {calibration_dir}")
        print(f"   카메라 매트릭스: {camera_matrix_path}")
        print(f"   왜곡 계수: {dist_coeffs_path}")
        return None, None
    
    try:
        camera_matrix = np.load(camera_matrix_path)
        dist_coeffs = np.load(dist_coeffs_path)
        
        print(f"✅ {camera_type} 카메라 캘리브레이션 데이터 로드 성공!")
        print(f"📁 경로: {calibration_dir}")
        print(f"📐 카메라 매트릭스:\n{camera_matrix}")
        print(f"🔧 왜곡 계수: {dist_coeffs}")
        
        return camera_matrix, dist_coeffs
        
    except Exception as e:
        print(f"❌ 캘리브레이션 데이터 로드 실패: {e}")
        return None, None

def test_calibration_realtime():
    """실시간 캘리브레이션 테스트"""
    
    # 카메라 선택
    print("📹 사용할 카메라를 선택하세요:")
    print("1. 전면 카메라 (/dev/frontcam)")
    print("2. 후면 카메라 (/dev/backcam)")
    print("3. 기본 CSI 카메라 (nvarguscamerasrc)")
    
    while True:
        choice = input("선택하세요 (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("❌ 잘못된 선택입니다. 1-3 중에서 선택하세요.")
    
    # 카메라 설정 및 캘리브레이션 데이터 로드
    if choice == '1':
        camera_device = "/dev/frontcam"
        camera_name = "전면 카메라"
        use_gstreamer = False
        camera_matrix, dist_coeffs = load_calibration_data("front")
    elif choice == '2':
        camera_device = "/dev/backcam" 
        camera_name = "후면 카메라"
        use_gstreamer = False
        camera_matrix, dist_coeffs = load_calibration_data("back")
    else:
        camera_device = None
        camera_name = "CSI 카메라"
        use_gstreamer = True
        camera_matrix, dist_coeffs = load_calibration_data("csi")
    
    if camera_matrix is None:
        return
    
    # 카메라 열기
    print(f"🎥 {camera_name} 연결 중...")
    
    if use_gstreamer:
        cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
    else:
        # V4L2 방식으로 시도
        cap = cv2.VideoCapture(v4l2_pipeline(camera_device), cv2.CAP_GSTREAMER)
        
        # 실패하면 직접 디바이스 번호로 시도
        if not cap.isOpened():
            print(f"⚠️  GStreamer 실패, 직접 디바이스로 시도: {camera_device}")
            cap = cv2.VideoCapture(camera_device)
    
    if not cap.isOpened():
        print(f"❌ {camera_name} 열기 실패!")
        return
    
    print(f"✅ {camera_name} 연결 성공!")
    print(f"📱 사용 중인 카메라: {camera_name}")
    print("\n조작법:")
    print("  ESC/q: 종료")
    print("  s: 스크린샷 저장")
    print("  SPACE: 원본/보정 화면 전환")
    print("  c: 카메라 정보 출력")
    print("-" * 50)
    
    show_comparison = True
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임 읽기 실패!")
            break
        
        frame_count += 1
        
        if show_comparison:
            # 왜곡 보정 적용
            undistorted_frame = cv2.undistort(frame, camera_matrix, dist_coeffs)
            
            # 두 화면을 나란히 배치
            h, w = frame.shape[:2]
            combined = np.zeros((h, w*2, 3), dtype=np.uint8)
            combined[:, :w] = frame
            combined[:, w:] = undistorted_frame
            
            # 텍스트 추가
            cv2.putText(combined, f"Original ({camera_name})", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(combined, f"Undistorted ({camera_name})", (w + 10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # FPS 표시
            cv2.putText(combined, f"Frame: {frame_count}", (10, h - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow(f'Calibration Test - {camera_name} (Original vs Undistorted)', combined)
            
        else:
            # 보정된 화면만 표시
            undistorted_frame = cv2.undistort(frame, camera_matrix, dist_coeffs)
            
            cv2.putText(undistorted_frame, f"Undistorted ({camera_name})", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(undistorted_frame, f"Frame: {frame_count}", (10, 450), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow(f'Calibration Test - {camera_name} (Undistorted Only)', undistorted_frame)
        
        # 키 입력 처리
        key = cv2.waitKey(1) & 0xFF
        
        if key == 27 or key == ord('q'):  # ESC 또는 'q'
            break
        elif key == ord(' '):  # SPACE - 화면 모드 전환
            show_comparison = not show_comparison
            cv2.destroyAllWindows()
            mode = "비교" if show_comparison else "보정만"
            print(f"🔄 화면 모드 변경: {mode}")
        elif key == ord('s'):  # 's' - 스크린샷 저장
            timestamp = cv2.getTickCount()
            if show_comparison:
                filename = f"calibration_test_{camera_name.replace(' ', '_')}_comparison_{timestamp}.jpg"
                cv2.imwrite(filename, combined)
            else:
                filename = f"calibration_test_{camera_name.replace(' ', '_')}_undistorted_{timestamp}.jpg"
                cv2.imwrite(filename, undistorted_frame)
            print(f"📸 스크린샷 저장: {filename}")
        elif key == ord('c'):  # 'c' - 카메라 정보
            print(f"\n📱 카메라 정보:")
            print(f"   이름: {camera_name}")
            print(f"   디바이스: {camera_device if not use_gstreamer else 'CSI (GStreamer)'}")
            print(f"   해상도: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
            print(f"   FPS: {cap.get(cv2.CAP_PROP_FPS)}")
            print(f"   프레임 카운트: {frame_count}")
    
    # 정리
    cap.release()
    cv2.destroyAllWindows()
    print("🔚 캘리브레이션 테스트 종료")

def test_calibration_with_saved_images():
    """저장된 이미지로 캘리브레이션 테스트"""
    
    print("📹 테스트할 이미지 카메라를 선택하세요:")
    print("1. 전면 카메라 이미지")
    print("2. 후면 카메라 이미지")
    
    while True:
        choice = input("선택하세요 (1-2): ").strip()
        if choice in ['1', '2']:
            break
        print("❌ 잘못된 선택입니다. 1-2 중에서 선택하세요.")
    
    # 선택에 따른 설정
    if choice == '1':
        camera_type = "front"
        image_folder_name = "checkerboard_images"
    else:
        camera_type = "back"
        image_folder_name = "checkerboard_images_back"
    
    # 캘리브레이션 데이터 로드
    camera_matrix, dist_coeffs = load_calibration_data(camera_type)
    if camera_matrix is None:
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_folder = os.path.join(script_dir, image_folder_name)
    
    # 체커보드 이미지 가져오기
    import glob
    image_files = sorted(glob.glob(os.path.join(image_folder, "checkerboard_*.jpg")))[:10]
    
    if not image_files:
        print(f"❌ {image_folder}에서 테스트할 이미지가 없습니다.")
        print(f"   checkerboard_*.jpg 파일을 확인하세요.")
        return
    
    print(f"🖼️  {len(image_files)}개 {camera_type} 카메라 이미지로 캘리브레이션 테스트")
    print("\n조작법:")
    print("  SPACE/→: 다음 이미지")
    print("  ←: 이전 이미지")
    print("  ESC/q: 종료")
    print("-" * 50)
    
    current_index = 0
    
    while True:
        image_path = image_files[current_index]
        filename = os.path.basename(image_path)
        
        # 이미지 읽기
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ 이미지 읽기 실패: {filename}")
            current_index = (current_index + 1) % len(image_files)
            continue
        
        # 왜곡 보정 적용
        undistorted_img = cv2.undistort(img, camera_matrix, dist_coeffs)
        
        # 두 화면을 나란히 배치
        h, w = img.shape[:2]
        combined = np.zeros((h, w*2, 3), dtype=np.uint8)
        combined[:, :w] = img
        combined[:, w:] = undistorted_img
        
        # 텍스트 추가
        cv2.putText(combined, "Original", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(combined, "Undistorted", (w + 10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        info_text = f"[{current_index+1}/{len(image_files)}] {filename}"
        cv2.putText(combined, info_text, (10, h - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow('Calibration Test - Saved Images', combined)
        
        # 키 입력 처리
        key = cv2.waitKey(0) & 0xFF
        
        if key == 27 or key == ord('q'):  # ESC 또는 'q'
            break
        elif key == ord(' ') or key == 83:  # SPACE 또는 오른쪽 화살표
            current_index = (current_index + 1) % len(image_files)
        elif key == 81:  # 왼쪽 화살표
            current_index = (current_index - 1) % len(image_files)
    
    cv2.destroyAllWindows()

def main():
    """메인 함수"""
    print("🎯 캘리브레이션 결과 테스트 프로그램")
    print("=" * 50)
    print("1. 실시간 카메라 테스트")
    print("2. 저장된 이미지 테스트")
    print("3. 종료")
    print("-" * 50)
    
    while True:
        choice = input("선택하세요 (1-3): ").strip()
        
        if choice == '1':
            test_calibration_realtime()
            break
        elif choice == '2':
            test_calibration_with_saved_images()
            break
        elif choice == '3':
            print("👋 프로그램 종료")
            break
        else:
            print("❌ 잘못된 선택입니다. 1-3 중에서 선택하세요.")

if __name__ == "__main__":
    main()
