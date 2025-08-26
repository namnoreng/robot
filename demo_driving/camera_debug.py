#!/usr/bin/env python3
import cv2 as cv
import time
import subprocess
import sys

def check_camera_capabilities():
    """카메라 하드웨어 정보 상세 분석"""
    print("=== 카메라 하드웨어 분석 ===")
    
    # V4L2 장치 정보 확인
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True)
        print("📷 연결된 카메라 장치:")
        print(result.stdout)
    except:
        print("❌ v4l2-ctl 명령어를 찾을 수 없습니다.")
    
    # 카메라 지원 형식 확인
    try:
        result = subprocess.run(['v4l2-ctl', '--list-formats-ext'], 
                              capture_output=True, text=True)
        print("\n📋 지원하는 형식과 FPS:")
        print(result.stdout)
    except:
        print("❌ 카메라 형식 정보를 가져올 수 없습니다.")

def test_different_backends():
    """다양한 백엔드로 테스트"""
    print("\n=== 백엔드별 성능 테스트 ===")
    
    backends = [
        (cv.CAP_V4L2, "V4L2"),
        (cv.CAP_GSTREAMER, "GStreamer"),
        (cv.CAP_FFMPEG, "FFmpeg")
    ]
    
    for backend_id, backend_name in backends:
        print(f"\n🔧 {backend_name} 백엔드 테스트:")
        
        cap = cv.VideoCapture(0, backend_id)
        if not cap.isOpened():
            print(f"   ❌ {backend_name} 백엔드 실패")
            continue
            
        # 320x240 설정
        cap.set(cv.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv.CAP_PROP_FPS, 30)
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
        
        time.sleep(0.5)
        
        # 실제 설정값 확인
        actual_fps = cap.get(cv.CAP_PROP_FPS)
        print(f"   📊 설정된 FPS: {actual_fps}")
        
        # 3초간 측정
        frame_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
        
        elapsed = time.time() - start_time
        measured_fps = frame_count / elapsed
        print(f"   ✅ 실제 FPS: {measured_fps:.1f}")
        
        cap.release()

def test_usb_direct():
    """USB 직접 접근 테스트"""
    print("\n=== USB 장치 직접 테스트 ===")
    
    # USB 장치 정보
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        print("🔌 USB 장치 목록:")
        for line in result.stdout.split('\n'):
            if 'Camera' in line or 'Video' in line or 'cam' in line.lower():
                print(f"   📹 {line}")
    except:
        print("❌ lsusb 명령어 실행 실패")
    
    # dmesg에서 카메라 관련 정보
    try:
        result = subprocess.run(['dmesg', '|', 'grep', '-i', 'camera'], 
                              shell=True, capture_output=True, text=True)
        if result.stdout:
            print("\n📋 시스템 로그 (카메라):")
            print(result.stdout[-1000:])  # 마지막 1000자만
    except:
        pass

def test_raw_capture():
    """가장 기본적인 캡처 테스트"""
    print("\n=== 원시 캡처 성능 테스트 ===")
    print("최소한의 설정으로 테스트")
    
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 카메라 열기 실패")
        return
    
    # 아무 설정도 하지 않은 기본 상태
    print("📊 기본 설정:")
    print(f"   해상도: {cap.get(cv.CAP_PROP_FRAME_WIDTH):.0f}x{cap.get(cv.CAP_PROP_FRAME_HEIGHT):.0f}")
    print(f"   FPS: {cap.get(cv.CAP_PROP_FPS):.0f}")
    print(f"   버퍼 크기: {cap.get(cv.CAP_PROP_BUFFERSIZE):.0f}")
    
    # 10초간 연속 캡처
    frame_count = 0
    start_time = time.time()
    
    while time.time() - start_time < 10:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
            
            # 1초마다 중간 결과 출력
            elapsed = time.time() - start_time
            if frame_count % 5 == 0:
                current_fps = frame_count / elapsed
                print(f"   📈 {elapsed:.1f}초: {current_fps:.1f}fps")
    
    total_elapsed = time.time() - start_time
    final_fps = frame_count / total_elapsed
    print(f"\n✅ 최종 결과: {final_fps:.1f}fps (총 {frame_count}프레임)")
    
    cap.release()

if __name__ == "__main__":
    print("=== Jetson Nano 카메라 디버깅 도구 ===")
    print("1. 카메라 하드웨어 정보")
    print("2. 백엔드별 성능 테스트") 
    print("3. USB 장치 분석")
    print("4. 원시 캡처 테스트")
    print("5. 전체 실행")
    
    choice = input("선택하세요 (1-5): ").strip()
    
    if choice == "1":
        check_camera_capabilities()
    elif choice == "2":
        test_different_backends()
    elif choice == "3":
        test_usb_direct()
    elif choice == "4":
        test_raw_capture()
    elif choice == "5":
        check_camera_capabilities()
        test_different_backends()
        test_usb_direct()
        test_raw_capture()
    else:
        print("전체 분석을 실행합니다.")
        check_camera_capabilities()
        test_different_backends()
        test_usb_direct()
        test_raw_capture()
