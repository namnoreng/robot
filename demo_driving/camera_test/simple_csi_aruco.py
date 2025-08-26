#!/usr/bin/env python3
"""
CSI 카메라 간단 ArUco 검출기
문제 해결을 위한 최소한의 코드
"""
import cv2 as cv
import numpy as np
import time
from cv2 import aruco

def simple_csi_aruco():
    """가장 간단한 CSI ArUco 검출"""
    print("=== 간단 CSI ArUco 검출 ===")
    
    # 간단한 GStreamer 파이프라인
    pipeline = (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=640, height=480, framerate=30/1 ! "
        "nvvidconv ! "
        "video/x-raw, width=640, height=480, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink"
    )
    
    print("🔧 GStreamer 파이프라인:")
    print(f"   {pipeline}")
    
    # 카메라 초기화
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("❌ CSI 카메라 열기 실패!")
        print("💡 확인사항:")
        print("   1. CSI 카메라가 연결되어 있는지")
        print("   2. 다른 프로그램에서 카메라를 사용하고 있지 않은지")
        print("   3. nvarguscamerasrc가 설치되어 있는지")
        
        # USB 카메라로 폴백 시도
        print("\n🔄 USB 카메라로 폴백 시도...")
        cap = cv.VideoCapture(0)
        if cap.isOpened():
            print("✅ USB 카메라 사용")
        else:
            print("❌ 모든 카메라 실패")
            return False
    else:
        print("✅ CSI 카메라 초기화 성공!")
    
    # ArUco 설정 (가장 기본적인 설정)
    aruco_dict = cv.aruco.Dictionary_get(cv.aruco.DICT_6X6_250)
    parameters = cv.aruco.DetectorParameters_create()
    
    # 검출을 쉽게 하는 관대한 설정
    parameters.minMarkerPerimeterRate = 0.01
    parameters.maxMarkerPerimeterRate = 10.0
    parameters.polygonalApproxAccuracyRate = 0.1
    parameters.minCornerDistanceRate = 0.01
    parameters.minDistanceToBorder = 1
    
    print("\n🎯 ArUco 마커 검출 시작")
    print("💡 팁:")
    print("   - 마커를 카메라에 가까이 대보세요 (10-30cm)")
    print("   - 마커가 잘 보이도록 조명을 조절하세요")
    print("   - 마커가 평평하고 깨끗한지 확인하세요")
    print("\n📋 조작법:")
    print("   - ESC: 종료")
    print("   - SPACE: 스크린샷")
    print("   - D: 딕셔너리 변경")
    print("")
    
    # 사용할 딕셔너리 목록
    dictionaries = [
        (cv.aruco.DICT_6X6_250, "6x6_250"),
        (cv.aruco.DICT_5X5_250, "5x5_250"),
        (cv.aruco.DICT_4X4_250, "4x4_250"),
        (cv.aruco.DICT_4X4_50, "4x4_50"),
    ]
    dict_index = 0
    
    # 통계
    frame_count = 0
    detection_count = 0
    start_time = time.time()
    last_detection_time = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ 프레임 읽기 실패")
            continue
        
        frame_count += 1
        
        # 현재 딕셔너리
        current_dict_id, current_dict_name = dictionaries[dict_index]
        current_aruco_dict = cv.aruco.Dictionary_get(current_dict_id)
        
        # 그레이스케일 변환
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        
        # ArUco 마커 검출
        corners, ids, _ = cv.aruco.detectMarkers(gray, current_aruco_dict, parameters=parameters)
        
        # 검출 결과 처리
        detected_this_frame = False
        if ids is not None and len(ids) > 0:
            detection_count += 1
            detected_this_frame = True
            last_detection_time = time.time()
            
            # 검출된 마커 그리기
            cv.aruco.drawDetectedMarkers(frame, corners, ids)
            
            # 각 마커 정보 표시
            for i, corner in enumerate(corners):
                marker_id = ids[i][0]
                
                # 마커 중심점 계산
                center = np.mean(corner[0], axis=0).astype(int)
                
                # 마커 정보 표시
                cv.putText(frame, f"ID: {marker_id}", 
                          (center[0] - 30, center[1] - 20), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # 마커 크기 계산
                marker_size = np.linalg.norm(corner[0][0] - corner[0][2])
                cv.putText(frame, f"Size: {marker_size:.0f}px", 
                          (center[0] - 30, center[1] + 20), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # 마커 중심에 점 표시
                cv.circle(frame, tuple(center), 5, (0, 255, 0), -1)
                
                print(f"🎯 마커 검출! ID: {marker_id}, 크기: {marker_size:.0f}px, 딕셔너리: {current_dict_name}")
        
        # 성능 정보 표시
        elapsed = time.time() - start_time
        if elapsed > 0:
            fps = frame_count / elapsed
            detection_rate = (detection_count / frame_count) * 100
            
            # 상태 정보
            cv.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv.putText(frame, f"Dict: {current_dict_name}", (10, 60), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 검출률 (색상으로 구분)
            if detection_rate > 10:
                color = (0, 255, 0)  # 녹색
            elif detection_rate > 1:
                color = (0, 255, 255)  # 노란색
            else:
                color = (0, 0, 255)  # 빨간색
                
            cv.putText(frame, f"Detection: {detection_rate:.1f}%", (10, 90), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 현재 상태
            if detected_this_frame:
                status_text = "DETECTING!"
                status_color = (0, 255, 0)
            elif time.time() - last_detection_time < 2:
                status_text = "RECENT DETECTION"
                status_color = (0, 255, 255)
            else:
                status_text = "SEARCHING..."
                status_color = (0, 165, 255)
            
            cv.putText(frame, status_text, (10, 120), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        # 도움말 표시
        cv.putText(frame, "ESC: Exit, SPACE: Screenshot, D: Change Dict", 
                  (10, frame.shape[0] - 10), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # 화면 표시
        cv.imshow('Simple CSI ArUco Detection', frame)
        
        # 키 입력 처리
        key = cv.waitKey(1) & 0xFF
        
        if key == 27:  # ESC - 종료
            break
        elif key == ord(' '):  # SPACE - 스크린샷
            filename = f"aruco_screenshot_{int(time.time())}.jpg"
            cv.imwrite(filename, frame)
            print(f"📸 스크린샷 저장: {filename}")
        elif key == ord('d') or key == ord('D'):  # D - 딕셔너리 변경
            dict_index = (dict_index + 1) % len(dictionaries)
            new_dict_name = dictionaries[dict_index][1]
            print(f"🔄 딕셔너리 변경: {new_dict_name}")
    
    # 정리
    cap.release()
    cv.destroyAllWindows()
    
    # 최종 결과
    print("\n" + "="*50)
    print("📊 검출 결과")
    print("="*50)
    print(f"총 프레임: {frame_count}")
    print(f"검출 성공: {detection_count}")
    if frame_count > 0:
        print(f"검출률: {(detection_count/frame_count)*100:.1f}%")
        print(f"평균 FPS: {frame_count/elapsed:.1f}")
    
    if detection_count == 0:
        print("\n❌ 마커 검출 실패!")
        print("💡 해결 방법:")
        print("   1. 다른 딕셔너리 마커 사용 (4x4, 5x5, 6x6)")
        print("   2. 마커를 더 크게 출력")
        print("   3. 조명 개선")
        print("   4. 마커를 카메라에 더 가까이")
        print("   5. aruco_debug.py로 상세 진단")
    else:
        print(f"\n✅ 마커 검출 성공! (총 {detection_count}회)")
    
    return detection_count > 0

if __name__ == "__main__":
    simple_csi_aruco()
