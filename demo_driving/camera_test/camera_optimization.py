#!/usr/bin/env python3
import cv2 as cv
import time

def test_resolution_performance():
    """해상도별 성능 최적화 테스트"""
    print("=== 해상도 최적화 테스트 ===")
    
    # GStreamer 백엔드 사용 (가장 좋은 성능)
    print("🔧 GStreamer 백엔드 사용")
    
    resolutions = [
        (160, 120, "QQVGA"),
        (320, 240, "QVGA"),
        (640, 480, "VGA"),
        (800, 600, "SVGA"),
        (1280, 720, "HD"),
        (1920, 1080, "FHD")
    ]
    
    for width, height, name in resolutions:
        print(f"\n📐 {name} ({width}x{height}) 테스트:")
        
        # GStreamer 백엔드로 카메라 열기
        cap = cv.VideoCapture(0, cv.CAP_GSTREAMER)
        
        if not cap.isOpened():
            print(f"   ❌ 카메라 열기 실패")
            continue
        
        # 해상도와 FPS 설정
        cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv.CAP_PROP_FPS, 30)
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
        
        # 설정 적용 대기
        time.sleep(1)
        
        # 실제 설정값 확인
        actual_w = cap.get(cv.CAP_PROP_FRAME_WIDTH)
        actual_h = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        actual_fps = cap.get(cv.CAP_PROP_FPS)
        
        print(f"   📊 설정: {actual_w:.0f}x{actual_h:.0f} @ {actual_fps:.0f}fps")
        
        # 5초간 성능 측정
        frame_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 5:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
                
                # 1초마다 중간 결과
                elapsed = time.time() - start_time
                if frame_count % 5 == 0:
                    current_fps = frame_count / elapsed
                    print(f"   📈 {elapsed:.1f}초: {current_fps:.1f}fps")
        
        total_elapsed = time.time() - start_time
        final_fps = frame_count / total_elapsed
        
        # 대역폭 계산
        bandwidth_mbps = (width * height * 3 * final_fps) / (1024 * 1024)
        
        print(f"   ✅ 최종 FPS: {final_fps:.1f}")
        print(f"   🌐 대역폭: {bandwidth_mbps:.1f} MB/s")
        
        # 목표 FPS 달성 여부
        if final_fps >= 15:
            print(f"   🎯 {name} 권장! (15fps 이상)")
        elif final_fps >= 10:
            print(f"   ⚡ {name} 양호 (10fps 이상)")
        else:
            print(f"   🐌 {name} 느림 (10fps 미만)")
        
        cap.release()

def test_gstreamer_direct():
    """GStreamer 직접 파이프라인 테스트"""
    print("\n=== GStreamer 직접 파이프라인 테스트 ===")
    
    # 다양한 GStreamer 파이프라인 테스트
    pipelines = [
        # 기본 USB 카메라
        ("v4l2src device=/dev/video0 ! videoconvert ! appsink", "USB 기본"),
        
        # 해상도 지정
        ("v4l2src device=/dev/video0 ! video/x-raw,width=320,height=240,framerate=30/1 ! videoconvert ! appsink", "320x240@30fps"),
        
        # MJPEG 압축 사용
        ("v4l2src device=/dev/video0 ! image/jpeg,width=320,height=240,framerate=30/1 ! jpegdec ! videoconvert ! appsink", "MJPEG 320x240"),
        
        # 더 낮은 해상도
        ("v4l2src device=/dev/video0 ! video/x-raw,width=160,height=120,framerate=30/1 ! videoconvert ! appsink", "160x120@30fps"),
    ]
    
    for pipeline, desc in pipelines:
        print(f"\n🔧 {desc} 테스트:")
        print(f"   파이프라인: {pipeline}")
        
        cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
        
        if not cap.isOpened():
            print(f"   ❌ 파이프라인 실패")
            continue
        
        # 3초간 성능 측정
        frame_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
        
        elapsed = time.time() - start_time
        fps = frame_count / elapsed
        
        print(f"   ✅ 성능: {fps:.1f}fps")
        
        if fps >= 20:
            print(f"   🚀 {desc} 최적!")
        elif fps >= 15:
            print(f"   ⚡ {desc} 양호!")
        
        cap.release()

def install_v4l2_utils():
    """v4l2-utils 설치 안내"""
    print("\n=== V4L2 유틸리티 설치 안내 ===")
    print("📦 카메라 상세 정보를 보려면 v4l2-utils가 필요합니다:")
    print("")
    print("설치 명령어:")
    print("sudo apt update")
    print("sudo apt install v4l2-utils")
    print("")
    print("설치 후 사용할 수 있는 명령어:")
    print("v4l2-ctl --list-devices")
    print("v4l2-ctl --list-formats-ext")
    print("v4l2-ctl --all")

if __name__ == "__main__":
    print("=== Jetson Nano 카메라 최적화 테스트 ===")
    print("1. 해상도별 성능 테스트 (GStreamer)")
    print("2. GStreamer 파이프라인 직접 테스트")
    print("3. V4L2 유틸리티 설치 안내")
    print("4. 전체 테스트")
    
    choice = input("선택하세요 (1-4): ").strip()
    
    if choice == "1":
        test_resolution_performance()
    elif choice == "2":
        test_gstreamer_direct()
    elif choice == "3":
        install_v4l2_utils()
    elif choice == "4":
        test_resolution_performance()
        test_gstreamer_direct()
        install_v4l2_utils()
    else:
        print("전체 테스트를 실행합니다.")
        test_resolution_performance()
        test_gstreamer_direct()
        install_v4l2_utils()
