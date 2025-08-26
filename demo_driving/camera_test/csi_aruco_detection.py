#!/usr/bin/env python3
"""
CSI 카메라를 이용한 ArUco 마커 인식
Jetson Nano CSI 카메라로 최적화된 ArUco 검출
"""
import cv2 as cv
import numpy as np
import time
from cv2 import aruco

def gstreamer_pipeline(
    capture_width=1280,
    capture_height=720,
    display_width=640,
    display_height=480,
    framerate=30,
    flip_method=0,
):
    """CSI 카메라용 GStreamer 파이프라인"""
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        f"width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        "nvvidconv flip-method=" + str(flip_method) + " ! "
        f"video/x-raw, width={display_width}, height={display_height}, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink max-buffers=1 drop=true"
    )

def setup_aruco_detector():
    """ArUco 검출기 설정"""
    # ArUco 딕셔너리 (6x6_250 사용)
    aruco_dict = cv.aruco.Dictionary_get(cv.aruco.DICT_6X6_250)
    
    # 검출 파라미터 설정
    parameters = cv.aruco.DetectorParameters_create()
    
    # CSI 카메라 최적화 파라미터
    parameters.adaptiveThreshWinSizeMin = 3
    parameters.adaptiveThreshWinSizeMax = 23
    parameters.adaptiveThreshWinSizeStep = 10
    parameters.adaptiveThreshConstant = 7
    
    # 검출 정확도 향상
    parameters.minMarkerPerimeterRate = 0.03
    parameters.maxMarkerPerimeterRate = 4.0
    parameters.polygonalApproxAccuracyRate = 0.03
    parameters.minCornerDistanceRate = 0.05
    parameters.minDistanceToBorder = 3
    
    # 에러 보정
    parameters.cornerRefinementMethod = cv.aruco.CORNER_REFINE_SUBPIX
    parameters.cornerRefinementWinSize = 5
    parameters.cornerRefinementMaxIterations = 30
    parameters.cornerRefinementMinAccuracy = 0.1
    
    return aruco_dict, parameters

def csi_aruco_detection():
    """CSI 카메라 ArUco 검출 메인 함수"""
    print("=== CSI 카메라 ArUco 마커 인식 ===")
    print("📹 CSI 카메라 초기화 중...")
    
    # 다양한 해상도 옵션
    resolution_options = [
        # (캡처 해상도, 디스플레이 해상도, 설명)
        ((1280, 720), (640, 480), "HD 캡처 → VGA 디스플레이"),
        ((1920, 1080), (640, 480), "FHD 캡처 → VGA 디스플레이"),
        ((640, 480), (640, 480), "VGA 직접"),
        ((1280, 720), (1280, 720), "HD 직접"),
    ]
    
    for i, ((cap_w, cap_h), (disp_w, disp_h), desc) in enumerate(resolution_options):
        print(f"{i+1}. {desc} - {cap_w}x{cap_h} → {disp_w}x{disp_h}")
    
    try:
        choice = int(input("해상도 선택 (1-4): ")) - 1
        if choice < 0 or choice >= len(resolution_options):
            choice = 0
    except:
        choice = 0
    
    (cap_w, cap_h), (disp_w, disp_h), desc = resolution_options[choice]
    print(f"✅ 선택: {desc}")
    
    # CSI 카메라 초기화
    pipeline = gstreamer_pipeline(
        capture_width=cap_w,
        capture_height=cap_h,
        display_width=disp_w,
        display_height=disp_h,
        framerate=30,
        flip_method=0
    )
    
    print("🔧 GStreamer 파이프라인:")
    print(f"   {pipeline}")
    
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("❌ CSI 카메라 열기 실패!")
        print("💡 확인사항:")
        print("   - CSI 카메라가 제대로 연결되었는지")
        print("   - nvarguscamerasrc가 설치되었는지")
        print("   - 권한 문제가 없는지")
        return False
    
    print("✅ CSI 카메라 초기화 성공!")
    
    # ArUco 검출기 설정
    aruco_dict, parameters = setup_aruco_detector()
    
    # 통계 변수
    frame_count = 0
    detection_count = 0
    start_time = time.time()
    
    # 마커별 검출 기록
    marker_stats = {}
    
    print("\n🎯 ArUco 마커 검출 시작")
    print("📋 조작법:")
    print("   - ESC: 종료")
    print("   - SPACE: 현재 프레임 저장")
    print("   - R: 통계 리셋")
    print("")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ 프레임 읽기 실패")
            continue
        
        frame_count += 1
        
        # ArUco 마커 검출
        corners, ids, _ = cv.aruco.detectMarkers(frame, aruco_dict, parameters=parameters)
        
        detected_this_frame = False
        if ids is not None and len(ids) > 0:
            detection_count += 1
            detected_this_frame = True
            
            # 검출된 마커 그리기
            cv.aruco.drawDetectedMarkers(frame, corners, ids)
            
            # 마커별 통계 업데이트
            for marker_id in ids.flatten():
                if marker_id not in marker_stats:
                    marker_stats[marker_id] = 0
                marker_stats[marker_id] += 1
            
            # 마커 정보 표시
            for i, corner in enumerate(corners):
                marker_id = ids[i][0]
                
                # 마커 중심점 계산
                center = np.mean(corner[0], axis=0).astype(int)
                
                # 마커 ID와 정보 표시
                cv.putText(frame, f"ID: {marker_id}", 
                          (center[0] - 30, center[1] - 10), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # 마커 크기 계산 (대략적)
                marker_size = np.linalg.norm(corner[0][0] - corner[0][2])
                cv.putText(frame, f"Size: {marker_size:.0f}", 
                          (center[0] - 30, center[1] + 15), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # 성능 및 통계 정보 표시
        elapsed = time.time() - start_time
        if elapsed > 0:
            fps = frame_count / elapsed
            detection_rate = (detection_count / frame_count) * 100
            
            # FPS 표시
            cv.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 검출률 표시
            color = (0, 255, 0) if detection_rate > 50 else (0, 255, 255) if detection_rate > 20 else (0, 0, 255)
            cv.putText(frame, f"Detection: {detection_rate:.1f}%", (10, 60), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 현재 검출 상태
            status = "DETECTED" if detected_this_frame else "SEARCHING"
            status_color = (0, 255, 0) if detected_this_frame else (0, 165, 255)
            cv.putText(frame, status, (10, 90), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            
            # 해상도 정보
            cv.putText(frame, f"{disp_w}x{disp_h}", (10, frame.shape[0] - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 마커 통계 표시 (우측 상단)
        if marker_stats:
            y_offset = 30
            cv.putText(frame, "Markers Found:", (frame.shape[1] - 200, y_offset), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            for marker_id, count in sorted(marker_stats.items()):
                y_offset += 20
                cv.putText(frame, f"ID {marker_id}: {count}", 
                          (frame.shape[1] - 200, y_offset), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # 화면 표시
        cv.imshow('CSI ArUco Detection', frame)
        
        # 키 입력 처리
        key = cv.waitKey(1) & 0xFF
        
        if key == 27:  # ESC - 종료
            break
        elif key == ord(' '):  # SPACE - 스크린샷
            filename = f"aruco_capture_{int(time.time())}.jpg"
            cv.imwrite(filename, frame)
            print(f"📸 스크린샷 저장: {filename}")
        elif key == ord('r') or key == ord('R'):  # R - 통계 리셋
            frame_count = 0
            detection_count = 0
            start_time = time.time()
            marker_stats.clear()
            print("🔄 통계 리셋")
    
    # 정리
    cap.release()
    cv.destroyAllWindows()
    
    # 최종 통계 출력
    print("\n" + "="*50)
    print("📊 CSI ArUco 검출 결과")
    print("="*50)
    print(f"총 프레임: {frame_count}")
    print(f"검출 성공: {detection_count}")
    print(f"검출률: {detection_rate:.1f}%")
    print(f"평균 FPS: {fps:.1f}")
    
    if marker_stats:
        print(f"\n검출된 마커:")
        for marker_id, count in sorted(marker_stats.items()):
            percentage = (count / frame_count) * 100
            print(f"  ID {marker_id}: {count}회 ({percentage:.1f}%)")
    else:
        print("\n검출된 마커 없음")
    
    return True

def test_csi_camera():
    """CSI 카메라 기본 테스트"""
    print("=== CSI 카메라 기본 테스트 ===")
    
    # 간단한 테스트
    pipeline = gstreamer_pipeline(640, 480, 640, 480, 30, 0)
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if cap.isOpened():
        print("✅ CSI 카메라 접근 가능")
        
        # 몇 프레임 테스트
        for i in range(10):
            ret, frame = cap.read()
            if ret:
                print(f"✅ 프레임 {i+1}: {frame.shape}")
            else:
                print(f"❌ 프레임 {i+1}: 읽기 실패")
        
        cap.release()
        return True
    else:
        print("❌ CSI 카메라 접근 실패")
        return False

if __name__ == "__main__":
    print("=== CSI 카메라 ArUco 마커 인식 ===")
    print("1. CSI 카메라 테스트")
    print("2. ArUco 마커 검출")
    print("3. 전체 실행")
    
    choice = input("선택하세요 (1-3): ").strip()
    
    if choice == "1":
        test_csi_camera()
    elif choice == "2":
        csi_aruco_detection()
    elif choice == "3":
        if test_csi_camera():
            print("\n✅ 기본 테스트 성공! ArUco 검출을 시작합니다.\n")
            csi_aruco_detection()
        else:
            print("❌ CSI 카메라 테스트 실패")
    else:
        print("ArUco 검출을 실행합니다.")
        csi_aruco_detection()
