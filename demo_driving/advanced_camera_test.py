#!/usr/bin/env python3
import cv2 as cv
import time
import subprocess

def force_resolution_test():
    """강제 해상도 설정 테스트"""
    print("=== 강제 해상도 설정 테스트 ===")
    
    # V4L2 명령어로 직접 해상도 설정 시도
    commands = [
        "v4l2-ctl --set-fmt-video=width=320,height=240,pixelformat=YUYV",
        "v4l2-ctl --set-fmt-video=width=160,height=120,pixelformat=YUYV", 
        "v4l2-ctl --set-fmt-video=width=640,height=480,pixelformat=MJPG"
    ]
    
    for cmd in commands:
        print(f"\n🔧 명령어 실행: {cmd}")
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            print(f"   결과: {result.stdout.strip()}")
            if result.stderr:
                print(f"   오류: {result.stderr.strip()}")
        except Exception as e:
            print(f"   실행 실패: {e}")
        
        # 설정 후 테스트
        print("   📊 설정 후 성능 테스트:")
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if cap.isOpened():
            # 3초간 측정
            frame_count = 0
            start_time = time.time()
            
            while time.time() - start_time < 3:
                ret, frame = cap.read()
                if ret:
                    frame_count += 1
            
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            
            # 실제 해상도 확인
            actual_w = cap.get(cv.CAP_PROP_FRAME_WIDTH)
            actual_h = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
            
            print(f"   ✅ 해상도: {actual_w:.0f}x{actual_h:.0f}, FPS: {fps:.1f}")
            cap.release()
        else:
            print("   ❌ 카메라 열기 실패")

def test_different_pixel_formats():
    """다양한 픽셀 형식 테스트"""
    print("\n=== 픽셀 형식별 성능 테스트 ===")
    
    # 카메라가 지원할 수 있는 다양한 형식
    formats = [
        (cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('Y','U','Y','V'), "YUYV"),
        (cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M','J','P','G'), "MJPG"),
        (cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('Y','U','Y','2'), "YUY2"),
        (cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('U','Y','V','Y'), "UYVY")
    ]
    
    for prop, fourcc, name in formats:
        print(f"\n🎥 {name} 형식 테스트:")
        
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print(f"   ❌ 카메라 열기 실패")
            continue
        
        # 형식 설정
        cap.set(prop, fourcc)
        cap.set(cv.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv.CAP_PROP_FPS, 30)
        
        time.sleep(0.5)
        
        # 실제 설정 확인
        actual_w = cap.get(cv.CAP_PROP_FRAME_WIDTH)
        actual_h = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        actual_fps = cap.get(cv.CAP_PROP_FPS)
        
        print(f"   📊 설정: {actual_w:.0f}x{actual_h:.0f} @ {actual_fps:.0f}fps")
        
        # 3초간 성능 측정
        frame_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
        
        elapsed = time.time() - start_time
        fps = frame_count / elapsed
        
        print(f"   ✅ 실제 FPS: {fps:.1f}")
        
        if fps > 10:
            print(f"   🚀 {name} 형식 추천!")
        
        cap.release()

def check_usb_power():
    """USB 전원 상태 확인"""
    print("\n=== USB 전원 및 연결 상태 ===")
    
    # USB 장치 전원 상태
    try:
        result = subprocess.run(['lsusb', '-t'], capture_output=True, text=True)
        print("📋 USB 트리:")
        print(result.stdout)
    except:
        print("❌ lsusb 명령어 실행 실패")
    
    # USB 전원 관리 확인
    try:
        result = subprocess.run(['cat', '/sys/bus/usb/devices/*/power/autosuspend'], 
                              capture_output=True, text=True)
        print("\n⚡ USB 전원 관리:")
        print(result.stdout)
    except:
        print("❌ USB 전원 상태 확인 실패")

if __name__ == "__main__":
    print("=== Jetson Nano 고급 카메라 진단 ===")
    print("1. 강제 해상도 설정 테스트")
    print("2. 픽셀 형식별 성능 테스트") 
    print("3. USB 전원 상태 확인")
    print("4. 전체 실행")
    
    choice = input("선택하세요 (1-4): ").strip()
    
    if choice == "1":
        force_resolution_test()
    elif choice == "2":
        test_different_pixel_formats()
    elif choice == "3":
        check_usb_power()
    elif choice == "4":
        force_resolution_test()
        test_different_pixel_formats()
        check_usb_power()
    else:
        print("전체 진단을 실행합니다.")
        force_resolution_test()
        test_different_pixel_formats()
        check_usb_power()
