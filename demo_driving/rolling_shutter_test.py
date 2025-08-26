import cv2 as cv
import numpy as np
import time
import platform
from cv2 import aruco

current_platform = platform.system()

def simple_camera_test():
    """순수 카메라 성능 테스트 - ArUco 없이"""
    print("=== 순수 카메라 성능 테스트 ===")
    print("ArUco 검출 없이 최대 FPS 테스트")
    print("ESC 키로 종료")
    
    # 카메라 초기화
    if current_platform == 'Windows':
        cap = cv.VideoCapture(0, cv.CAP_DSHOW)
    else:
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
    
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return
    
    # Jetson Nano 최적화 설정
    print("📝 Jetson Nano 최적화 설정 적용...")
    
    # 해상도별 테스트
    resolutions = [
        (160, 120, "QQVGA"),
        (320, 240, "QVGA"), 
        (640, 480, "VGA")
    ]
    
    for width, height, name in resolutions:
        print(f"\n🔍 {name} ({width}x{height}) 테스트:")
        
        cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv.CAP_PROP_FPS, 30)
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
        
        # Jetson Nano 특화 설정
        cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M','J','P','G'))
        cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 수동 노출
        cap.set(cv.CAP_PROP_EXPOSURE, -6)  # 빠른 노출
        
        time.sleep(0.5)  # 설정 적용 대기
        
        # 실제 설정값 확인
        actual_w = cap.get(cv.CAP_PROP_FRAME_WIDTH)
        actual_h = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        actual_fps = cap.get(cv.CAP_PROP_FPS)
        print(f"   실제 설정: {actual_w:.0f}x{actual_h:.0f} @ {actual_fps:.0f}fps")
        
        # 5초간 FPS 측정
        test_duration = 5
        frame_count = 0
        start_time = time.time()
        fps_samples = []
        
        while time.time() - start_time < test_duration:
            ret, frame = cap.read()
            if not ret:
                continue
                
            frame_count += 1
            current_time = time.time()
            
            if frame_count % 10 == 0:  # 10프레임마다 FPS 계산
                elapsed = current_time - start_time
                if elapsed > 0:
                    current_fps = frame_count / elapsed
                    fps_samples.append(current_fps)
                    print(f"   📊 현재 FPS: {current_fps:.1f}")
        
        if fps_samples:
            avg_fps = sum(fps_samples) / len(fps_samples)
            max_fps = max(fps_samples)
            print(f"   ✅ {name} 결과: 평균 {avg_fps:.1f}fps, 최대 {max_fps:.1f}fps")
        
        print(f"   🔧 USB 대역폭 사용량: {width*height*3*avg_fps/1024/1024:.1f} MB/s")
    
    cap.release()
    cv.destroyAllWindows()

def jetson_hardware_info():
    """Jetson Nano 하드웨어 정보 출력"""
    print("\n=== Jetson Nano 하드웨어 분석 ===")
    print("🔍 5fps 한계의 가능한 원인들:")
    print("")
    print("1. USB 대역폭 제한:")
    print("   - USB 2.0: 최대 480Mbps (실제 ~300Mbps)")
    print("   - 640x480x3x30fps = ~220Mbps 필요")
    print("   - USB 오버헤드로 실제로는 더 많이 필요")
    print("")
    print("2. Jetson Nano CPU 제한:")
    print("   - ARM Cortex-A57 4코어 @ 1.43GHz")
    print("   - OpenCV 연산이 CPU 집약적")
    print("   - 열 조절로 인한 클럭 다운")
    print("")
    print("3. 메모리 대역폭:")
    print("   - 4GB LPDDR4 @ 1600MHz")
    print("   - CPU/GPU 공유 메모리")
    print("   - 이미지 복사 오버헤드")
    print("")
    print("4. 카메라 드라이버:")
    print("   - V4L2 드라이버 최적화 필요")
    print("   - UVC 카메라 호환성 문제")
    print("")
    print("💡 개선 방안:")
    print("   - 더 낮은 해상도 사용 (320x240 이하)")
    print("   - MJPEG 압축 활용")
    print("   - GPU 가속 활용 (GStreamer)")
    print("   - 전용 CSI 카메라 사용")

def test_jetson_optimized():
    """Jetson Nano 전용 최적화 테스트"""
    print("=== Jetson Nano 전용 최적화 테스트 ===")
    
    # GStreamer 파이프라인 시도
    gst_pipeline = (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=320, height=240, format=NV12, framerate=30/1 ! "
        "nvvidconv ! video/x-raw, format=BGRx ! "
        "videoconvert ! video/x-raw, format=BGR ! appsink"
    )
    
    print("🔧 GStreamer 파이프라인 테스트...")
    cap = cv.VideoCapture(gst_pipeline, cv.CAP_GSTREAMER)
    
    if cap.isOpened():
        print("✅ GStreamer 성공! CSI 카메라 사용 중")
        frame_count = 0
        start_time = time.time()
        
        for i in range(150):  # 5초간 30fps 기대
            ret, frame = cap.read()
            if ret:
                frame_count += 1
        
        elapsed = time.time() - start_time
        fps = frame_count / elapsed
        print(f"🚀 GStreamer FPS: {fps:.1f}")
        cap.release()
    else:
        print("❌ GStreamer 실패 - USB 카메라로 폴백")
        simple_camera_test()
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        current_time = time.time()
        elapsed = current_time - start_time
        
        if elapsed >= 1.0:
            fps = frame_count / elapsed
            print(f"🚀 실제 FPS: {fps:.1f}")
            frame_count = 0
            start_time = current_time
        
        # 최소한의 화면 표시
        cv.imshow('Pure Camera Test', frame)
        
        if cv.waitKey(1) & 0xFF == 27:  # ESC
            break
    
    cap.release()
    cv.destroyAllWindows()

def test_rolling_shutter_settings():
    """Rolling Shutter 효과를 테스트하는 함수 - 성능 최적화 버전"""
    
    print("=== Rolling Shutter 테스트 시작 (성능 최적화) ===")
    print("빠른 움직임으로 Rolling Shutter 효과를 확인하세요")
    print("키 조작:")
    print("  's': 현재 설정 저장")
    print("  '1': 기본 설정 (640x480@30fps)")
    print("  '2': Rolling Shutter 최소화 1")
    print("  '3': Rolling Shutter 최소화 2")
    print("  '4': 고속 촬영 설정")
    print("  '5': 초고속 모드 (320x240@60fps)")
    print("  'r': 설정 리셋")
    print("  'q': 종료")
    print("-" * 50)
    
    # 카메라 초기화 - 최대 성능 우선
    if current_platform == 'Windows':
        cap = cv.VideoCapture(0, cv.CAP_DSHOW)
    elif current_platform == 'Linux':
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
    else:
        cap = cv.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return
    
    print("📹 카메라 성능 최적화 설정 중...")
    
    # 즉시 최적 설정 적용
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv.CAP_PROP_FPS, 60)
    cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv.CAP_PROP_EXPOSURE, -6)
    
    # 실제 설정된 값 확인
    actual_width = cap.get(cv.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
    actual_fps = cap.get(cv.CAP_PROP_FPS)
    print(f"✅ 카메라 설정: {int(actual_width)}x{int(actual_height)}@{int(actual_fps)}fps")
    
    # ArUco 설정 - 성능 테스트를 위해 최소화
    print("🔍 ArUco 설정 건너뛰기 (순수 카메라 성능 테스트)")
    # marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
    # param_markers = aruco.DetectorParameters_create()
    
    current_setting = "기본 설정"
    frame_count = 0
    fps_timer = time.time()
    fps_display = 0
    
    # 설정별 함수들
    def apply_basic_setting():
        """기본 카메라 설정 - 성능 최적화"""
        try:
            cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv.CAP_PROP_FPS, 30)
            cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.75)
            cap.set(cv.CAP_PROP_EXPOSURE, -6)
            cap.set(cv.CAP_PROP_GAIN, 10)
            cap.set(cv.CAP_PROP_BRIGHTNESS, 128)
            print("✅ 기본 설정 적용 (640x480@30fps)")
            return "기본 설정"
        except Exception as e:
            print(f"기본 설정 실패: {e}")
            return "설정 실패"
    
    def apply_rolling_shutter_fix_1():
        """Rolling Shutter 최소화 설정 1 - 성능 우선"""
        try:
            cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv.CAP_PROP_FPS, 30)
            cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv.CAP_PROP_EXPOSURE, -8)
            cap.set(cv.CAP_PROP_GAIN, 35)  # 적당한 게인
            cap.set(cv.CAP_PROP_BRIGHTNESS, 135)
            print("✅ Rolling Shutter 최소화 1 적용")
            return "RS 최소화 1"
            cap.set(cv.CAP_PROP_CONTRAST, 140)        # 대비 증가
            cap.set(cv.CAP_PROP_AUTO_WB, 0)           # 화이트밸런스 고정
            cap.set(cv.CAP_PROP_WB_TEMPERATURE, 4000)
            cap.set(cv.CAP_PROP_FPS, 30)
            return "Rolling Shutter 최소화 1 (짧은 노출)"
        except Exception as e:
            print(f"설정 1 실패: {e}")
            return "설정 실패"
    
    def apply_rolling_shutter_fix_2():
        """Rolling Shutter 최소화 설정 2 - 극짧은 노출"""
        try:
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 수동 노출 모드
            cap.set(cv.CAP_PROP_EXPOSURE, -9)         # 극짧은 노출
            cap.set(cv.CAP_PROP_GAIN, 60)             # 높은 게인
            cap.set(cv.CAP_PROP_BRIGHTNESS, 160)      # 높은 밝기
            cap.set(cv.CAP_PROP_CONTRAST, 150)        # 높은 대비
            cap.set(cv.CAP_PROP_SATURATION, 120)      # 채도 증가
            cap.set(cv.CAP_PROP_AUTO_WB, 0)           # 화이트밸런스 고정
            cap.set(cv.CAP_PROP_WB_TEMPERATURE, 4200)
            cap.set(cv.CAP_PROP_FPS, 30)
            return "Rolling Shutter 최소화 2 (극짧은 노출)"
        except Exception as e:
            print(f"설정 2 실패: {e}")
            return "설정 실패"
    
    def apply_high_speed_setting():
        """고속 촬영 설정 - 60fps"""
        try:
            cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, 360)
            cap.set(cv.CAP_PROP_FPS, 60)
            cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv.CAP_PROP_EXPOSURE, -7)
            cap.set(cv.CAP_PROP_GAIN, 45)
            cap.set(cv.CAP_PROP_BRIGHTNESS, 145)
            print("✅ 고속 촬영 설정 적용 (640x360@60fps)")
            return "고속 60fps"
        except Exception as e:
            print(f"고속 설정 실패: {e}")
            return "설정 실패"
    
    def apply_ultra_fast_setting():
        """초고속 촬영 설정 - 최대 성능"""
        try:
            cap.set(cv.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv.CAP_PROP_FPS, 60)
            cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv.CAP_PROP_EXPOSURE, -8)
            cap.set(cv.CAP_PROP_GAIN, 40)
            cap.set(cv.CAP_PROP_BRIGHTNESS, 140)
            print("✅ 초고속 모드 적용 (320x240@60fps)")
            return "초고속 60fps"
        except Exception as e:
            print(f"초고속 설정 실패: {e}")
            return "설정 실패"
        except Exception as e:
            print(f"고속 설정 실패: {e}")
            return "설정 실패"
    
    def reset_camera():
        """카메라 설정 리셋"""
        try:
            cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv.CAP_PROP_FPS, 30)
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.75)
            cap.set(cv.CAP_PROP_EXPOSURE, -1)
            cap.set(cv.CAP_PROP_GAIN, 0)
            cap.set(cv.CAP_PROP_BRIGHTNESS, 128)
            cap.set(cv.CAP_PROP_CONTRAST, 128)
            cap.set(cv.CAP_PROP_SATURATION, 128)
            cap.set(cv.CAP_PROP_AUTO_WB, 1)
            return "설정 리셋 완료"
        except Exception as e:
            print(f"리셋 실패: {e}")
            return "리셋 실패"
    
    def save_current_frame(frame, setting_name):
        """현재 프레임을 이미지로 저장"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"rolling_shutter_test_{setting_name}_{timestamp}.jpg"
        cv.imwrite(filename, frame)
        print(f"✅ 프레임 저장: {filename}")
    
    # 기본 설정 적용
    current_setting = apply_basic_setting()
    
    # 성능 최적화 변수
    aruco_skip_counter = 0
    ARUCO_SKIP_FRAMES = 2  # 매 3프레임마다 ArUco 검출
    last_ids = None
    last_corners = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임을 읽을 수 없습니다.")
            break
        
        # FPS 계산
        frame_count += 1
        current_time = time.time()
        if current_time - fps_timer >= 1.0:
            fps_display = frame_count
            frame_count = 0
            fps_timer = current_time
        
        # ArUco 마커 검출 - 성능 테스트를 위해 완전히 비활성화
        ids = None
        corners = None
        
        # 성능 테스트 모드: ArUco 검출 건너뛰기
        # aruco_skip_counter += 1
        # if aruco_skip_counter % (ARUCO_SKIP_FRAMES + 1) == 0:
        #     # 실제 ArUco 검출 수행
        #     gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        #     corners, ids, _ = aruco.detectMarkers(gray, marker_dict, parameters=param_markers)
        #     last_ids = ids
        #     last_corners = corners
        # else:
        #     # 이전 검출 결과 재사용
        #     ids = last_ids
        #     corners = last_corners
        
        # 마커 표시도 비활성화 (성능 테스트)
        # if ids is not None and corners is not None:
        #     aruco.drawDetectedMarkers(frame, corners, ids)
        #     # 첫 번째 마커만 ID 표시 (성능 향상)
        #     if len(ids) > 0:
        #         marker_id = ids[0][0]
        #         center_x = int(corners[0][0][:, 0].mean())
        #         center_y = int(corners[0][0][:, 1].mean())
        #         cv.putText(frame, f"ID: {marker_id}", 
        #                   (center_x - 30, center_y - 10), 
        #                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 정보 표시 (최소화 - 성능 우선)
        cv.putText(frame, f"FPS: {fps_display}", 
                  (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 사용법 표시 생략 (성능 향상)
        # cv.putText(frame, "1,2,3,4,5:settings s:save q:quit", 
        #           (10, frame.shape[0] - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # 화면 표시
        cv.imshow('Rolling Shutter Test', frame)
        
        # 키 입력 처리 (논블로킹)
        key = cv.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("테스트 종료")
            break
        elif key == ord('s'):
            save_current_frame(frame, current_setting.replace(" ", "_"))
        elif key == ord('1'):
            current_setting = apply_basic_setting()
        elif key == ord('2'):
            current_setting = apply_rolling_shutter_fix_1()
        elif key == ord('3'):
            current_setting = apply_rolling_shutter_fix_2()
        elif key == ord('4'):
            current_setting = apply_high_speed_setting()
        elif key == ord('5'):
            current_setting = apply_ultra_fast_setting()
        elif key == ord('r'):
            current_setting = reset_camera()
            print(f"✅ {current_setting}")
    
    # 정리
    cap.release()
    cv.destroyAllWindows()
    print("=== Rolling Shutter 테스트 완료 ===")

def print_camera_properties(cap):
    """현재 카메라 설정값들을 출력"""
    print("\n=== 현재 카메라 설정값 ===")
    properties = {
        'FRAME_WIDTH': cv.CAP_PROP_FRAME_WIDTH,
        'FRAME_HEIGHT': cv.CAP_PROP_FRAME_HEIGHT,
        'FPS': cv.CAP_PROP_FPS,
        'EXPOSURE': cv.CAP_PROP_EXPOSURE,
        'GAIN': cv.CAP_PROP_GAIN,
        'BRIGHTNESS': cv.CAP_PROP_BRIGHTNESS,
        'CONTRAST': cv.CAP_PROP_CONTRAST,
        'SATURATION': cv.CAP_PROP_SATURATION,
        'AUTO_EXPOSURE': cv.CAP_PROP_AUTO_EXPOSURE,
        'AUTO_WB': cv.CAP_PROP_AUTO_WB,
        'WB_TEMPERATURE': cv.CAP_PROP_WB_TEMPERATURE,
    }
    
    for name, prop in properties.items():
        try:
            value = cap.get(prop)
            print(f"{name}: {value}")
        except:
            print(f"{name}: 지원하지 않음")
    print("=" * 30)

if __name__ == "__main__":
    print("=== Jetson Nano 카메라 성능 분석 ===")
    print("1. 순수 카메라 성능 테스트 (해상도별)")
    print("2. Rolling Shutter 테스트 (ArUco 포함)")
    print("3. Jetson 하드웨어 한계 분석")
    print("4. Jetson 전용 최적화 테스트 (GStreamer)")
    
    choice = input("선택하세요 (1-4): ").strip()
    
    if choice == "1":
        simple_camera_test()
    elif choice == "2":
        test_rolling_shutter_settings()
    elif choice == "3":
        jetson_hardware_info()
    elif choice == "4":
        test_jetson_optimized()
    else:
        print("잘못된 선택입니다. 하드웨어 분석을 출력합니다.")
        jetson_hardware_info()
