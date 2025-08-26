#!/usr/bin/env python3
"""
카메라 형식별 실제 성능 테스트
v4l2-ctl 결과를 바탕으로 최적화된 설정 테스트
"""
import cv2 as cv
import time

def test_optimal_formats():
    """최적 형식별 성능 테스트"""
    print("=== 카메라 최적 형식 성능 테스트 ===")
    print("v4l2-ctl 결과를 바탕으로 실제 성능 측정")
    print("")
    
    # 테스트할 설정들 (형식, 해상도, 예상 FPS)
    test_configs = [
        # MJPG (압축) - 최고 성능 기대
        ("MJPG", 160, 120, 30, "초고속 처리용"),
        ("MJPG", 320, 240, 30, "ArUco 검출 최적"),
        ("MJPG", 640, 480, 30, "품질 중시"),
        
        # YUYV (RAW) - 품질 최고
        ("YUYV", 160, 120, 30, "RAW 최소"),
        ("YUYV", 320, 240, 30, "RAW 중간"),
        ("YUYV", 640, 480, 30, "RAW 최대"),
        
        # H264 (하드웨어 인코딩) - 특수용도
        ("H264", 320, 240, 30, "하드웨어 인코딩"),
        ("H264", 640, 480, 30, "H264 고품질"),
    ]
    
    results = []
    
    for format_name, width, height, target_fps, description in test_configs:
        print(f"\n📹 {format_name} {width}x{height} 테스트 ({description})")
        
        # 형식별 FOURCC 설정
        if format_name == "MJPG":
            fourcc = cv.VideoWriter_fourcc('M','J','P','G')
        elif format_name == "YUYV":
            fourcc = cv.VideoWriter_fourcc('Y','U','Y','V')
        elif format_name == "H264":
            fourcc = cv.VideoWriter_fourcc('H','2','6','4')
        
        # V4L2 백엔드 사용 (GStreamer보다 설정 제어가 쉬움)
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        
        if not cap.isOpened():
            print(f"   ❌ 카메라 열기 실패")
            continue
        
        # 설정 적용
        cap.set(cv.CAP_PROP_FOURCC, fourcc)
        cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv.CAP_PROP_FPS, target_fps)
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
        
        # 설정 적용 대기
        time.sleep(0.5)
        
        # 실제 설정값 확인
        actual_w = cap.get(cv.CAP_PROP_FRAME_WIDTH)
        actual_h = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        actual_fps = cap.get(cv.CAP_PROP_FPS)
        actual_fourcc = cap.get(cv.CAP_PROP_FOURCC)
        
        # FOURCC를 문자열로 변환
        fourcc_str = "".join([chr((int(actual_fourcc) >> 8 * i) & 0xFF) for i in range(4)])
        
        print(f"   📊 설정: {actual_w:.0f}x{actual_h:.0f} @ {actual_fps:.0f}fps ({fourcc_str})")
        
        # 5초간 성능 측정
        frame_count = 0
        start_time = time.time()
        test_duration = 5
        
        fps_samples = []
        
        while time.time() - start_time < test_duration:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
                
                # 1초마다 중간 FPS 계산
                elapsed = time.time() - start_time
                if frame_count % 10 == 0 and elapsed > 0:
                    current_fps = frame_count / elapsed
                    fps_samples.append(current_fps)
                    print(f"   📈 {elapsed:.1f}초: {current_fps:.1f}fps")
        
        total_elapsed = time.time() - start_time
        final_fps = frame_count / total_elapsed
        
        # 성능 평가
        if final_fps >= 25:
            grade = "🚀 최고"
        elif final_fps >= 20:
            grade = "⚡ 우수"
        elif final_fps >= 15:
            grade = "✅ 양호"
        elif final_fps >= 10:
            grade = "⚠️  보통"
        else:
            grade = "🐌 느림"
        
        print(f"   {grade}: {final_fps:.1f}fps")
        
        # 대역폭 계산
        if format_name == "YUYV":
            bandwidth = (width * height * 2 * final_fps) / (1024 * 1024)  # YUV 2바이트
        else:
            bandwidth = "압축됨"
        
        if isinstance(bandwidth, float):
            print(f"   🌐 대역폭: {bandwidth:.1f} MB/s")
        else:
            print(f"   🌐 대역폭: {bandwidth}")
        
        results.append({
            'format': format_name,
            'resolution': f"{width}x{height}",
            'target_fps': target_fps,
            'actual_fps': final_fps,
            'description': description,
            'grade': grade
        })
        
        cap.release()
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 성능 테스트 결과 요약")
    print("="*60)
    
    # 성능순 정렬
    results.sort(key=lambda x: x['actual_fps'], reverse=True)
    
    print(f"{'순위':<4} {'형식':<6} {'해상도':<10} {'FPS':<8} {'평가':<8} {'용도'}")
    print("-" * 60)
    
    for i, result in enumerate(results[:5], 1):  # 상위 5개만 표시
        print(f"{i:<4} {result['format']:<6} {result['resolution']:<10} "
              f"{result['actual_fps']:<8.1f} {result['grade']:<8} {result['description']}")
    
    # 권장 설정
    print("\n🎯 권장 설정:")
    top_result = results[0]
    if top_result['actual_fps'] >= 20:
        print(f"   최고 성능: {top_result['format']} {top_result['resolution']} ({top_result['actual_fps']:.1f}fps)")
        print(f"   ArUco 검출에 최적!")
    else:
        print(f"   최고 성능도 {top_result['actual_fps']:.1f}fps로 제한적입니다.")
        print(f"   소프트웨어 최적화가 필요합니다.")

def test_aruco_with_optimal():
    """최적 설정으로 ArUco 검출 테스트"""
    print("\n=== ArUco 검출 최적화 테스트 ===")
    
    # MJPG 320x240 (가장 균형잡힌 설정 예상)
    cap = cv.VideoCapture(0, cv.CAP_V4L2)
    
    if not cap.isOpened():
        print("❌ 카메라 열기 실패")
        return
    
    # 최적 설정 적용
    cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M','J','P','G'))
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv.CAP_PROP_FPS, 30)
    cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
    
    # Rolling shutter 최적화
    cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 수동 노출
    cap.set(cv.CAP_PROP_EXPOSURE, -6)  # 빠른 노출
    cap.set(cv.CAP_PROP_GAIN, 50)  # 적당한 게인
    
    time.sleep(1)
    
    print("🔧 MJPG 320x240 + ArUco 검출 테스트")
    print("📋 ESC 키로 종료")
    
    # ArUco 설정
    aruco_dict = cv.aruco.Dictionary_get(cv.aruco.DICT_6X6_250)
    parameters = cv.aruco.DetectorParameters_create()
    
    # ArUco 검출 최적화
    parameters.adaptiveThreshWinSizeMin = 3
    parameters.adaptiveThreshWinSizeMax = 23
    parameters.adaptiveThreshWinSizeStep = 10
    
    frame_count = 0
    detection_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        frame_count += 1
        
        # ArUco 검출
        corners, ids, _ = cv.aruco.detectMarkers(frame, aruco_dict, parameters=parameters)
        
        if ids is not None:
            detection_count += 1
            # 마커 그리기
            cv.aruco.drawDetectedMarkers(frame, corners, ids)
        
        # FPS 계산 및 표시
        elapsed = time.time() - start_time
        if elapsed > 0:
            fps = frame_count / elapsed
            detection_rate = (detection_count / frame_count) * 100
            
            cv.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv.putText(frame, f"Detection: {detection_rate:.1f}%", (10, 60), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv.imshow('ArUco Optimized Test', frame)
        
        if cv.waitKey(1) & 0xFF == 27:  # ESC 키
            break
    
    cap.release()
    cv.destroyAllWindows()
    
    print(f"\n✅ 테스트 완료:")
    print(f"   평균 FPS: {fps:.1f}")
    print(f"   ArUco 검출률: {detection_rate:.1f}%")

if __name__ == "__main__":
    print("=== 카메라 최적화 테스트 도구 ===")
    print("1. 형식별 성능 테스트")
    print("2. ArUco + 최적 설정 테스트")
    print("3. 전체 테스트")
    
    choice = input("선택하세요 (1-3): ").strip()
    
    if choice == "1":
        test_optimal_formats()
    elif choice == "2":
        test_aruco_with_optimal()
    elif choice == "3":
        test_optimal_formats()
        test_aruco_with_optimal()
    else:
        print("전체 테스트를 실행합니다.")
        test_optimal_formats()
        test_aruco_with_optimal()
