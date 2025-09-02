#!/usr/bin/env python3
"""
CSI 카메라 5x5 ArUco 마커 전용 인식 시스템
간단하고 최적화된 5x5 전용 검출기
"""
import cv2 as cv
import numpy as np
import time
import os
from cv2 import aruco

def load_calibration_data():
    """캘리브레이션 데이터 로드"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    calibration_dir = os.path.join(script_dir, "calibration_result")
    
    # 전면 카메라 캘리브레이션 사용 (기본값)
    camera_matrix_path = os.path.join(calibration_dir, "camera_front_matrix.npy")
    dist_coeffs_path = os.path.join(calibration_dir, "dist_front_coeffs.npy")
    
    if os.path.exists(camera_matrix_path) and os.path.exists(dist_coeffs_path):
        try:
            camera_matrix = np.load(camera_matrix_path)
            dist_coeffs = np.load(dist_coeffs_path)
            print("✅ 캘리브레이션 데이터 로드 성공 - 왜곡 보정 활성화")
            return camera_matrix, dist_coeffs
        except Exception as e:
            print(f"⚠️ 캘리브레이션 로드 실패: {e}")
    else:
        print("⚠️ 캘리브레이션 파일 없음 - 왜곡 보정 비활성화")
    
    return None, None

def gstreamer_pipeline(capture_width=640, capture_height=480, 
                      display_width=640, display_height=480, 
                      framerate=30, flip_method=0, device="/dev/frontcam"):
    """CSI 카메라용 GStreamer 파이프라인"""
    return (
        f"nvarguscamerasrc sensor-id=1 ! "
        "video/x-raw(memory:NVMM), "
        f"width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        "nvvidconv flip-method=" + str(flip_method) + " ! "
        f"video/x-raw, width={display_width}, height={display_height}, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink max-buffers=1 drop=true"
    )

def setup_5x5_aruco():
    """5x5 ArUco 딕셔너리 설정"""
    # 5x5_250 딕셔너리 사용 (가장 일반적)
    aruco_dict = cv.aruco.Dictionary_get(cv.aruco.DICT_5X5_250)
    
    # 검출 파라미터 - 5x5에 최적화
    parameters = cv.aruco.DetectorParameters_create()
    
    # 5x5 마커에 최적화된 파라미터
    parameters.adaptiveThreshWinSizeMin = 3
    parameters.adaptiveThreshWinSizeMax = 23
    parameters.adaptiveThreshWinSizeStep = 10
    parameters.adaptiveThreshConstant = 7
    
    # 검출 정확도 향상
    parameters.minMarkerPerimeterRate = 0.03  # 최소 마커 둘레 비율
    parameters.maxMarkerPerimeterRate = 4.0   # 최대 마커 둘레 비율
    parameters.polygonalApproxAccuracyRate = 0.03
    parameters.minCornerDistanceRate = 0.05
    parameters.minDistanceToBorder = 3
    
    # 검출 관대함 설정 (5x5는 더 관대하게)
    parameters.cornerRefinementMethod = cv.aruco.CORNER_REFINE_SUBPIX
    parameters.cornerRefinementWinSize = 5
    parameters.cornerRefinementMaxIterations = 30
    parameters.cornerRefinementMinAccuracy = 0.1
    
    # 5x5 특화 설정
    parameters.minMarkerLengthRatioOriginalImg = 0.02  # 작은 마커도 검출
    
    return aruco_dict, parameters

def run_5x5_aruco_detection():
    """5x5 ArUco 마커 검출 실행"""
    print("=== 5x5 ArUco 마커 전용 검출 시스템 ===")
    print("📐 해상도 선택:")
    print("1. 640x480 (표준)")
    print("2. 1280x720 (고화질)")
    print("3. 320x240 (고속)")
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == "2":
        cap_w, cap_h, disp_w, disp_h = 1280, 720, 640, 480
        desc = "HD→VGA"
    elif choice == "3":
        cap_w, cap_h, disp_w, disp_h = 320, 240, 320, 240
        desc = "QVGA"
    else:
        cap_w, cap_h, disp_w, disp_h = 640, 480, 640, 480
        desc = "VGA"
    
    print(f"✅ 선택: {desc} ({cap_w}x{cap_h})")
    
    # CSI 카메라 초기화 (backcam 우선)
    pipeline = gstreamer_pipeline(cap_w, cap_h, disp_w, disp_h, 30, 0, "/dev/backcam")
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("❌ CSI backcam 실패 - /dev/video1로 재시도")
        cap = cv.VideoCapture(1)  # /dev/video1 (backcam)
        if not cap.isOpened():
            print("❌ backcam 실패 - frontcam으로 폴백")
            cap = cv.VideoCapture(0)  # /dev/video0 (frontcam)
            if not cap.isOpened():
                print("❌ 모든 카메라 실패")
                return False
    
    print("✅ 카메라 초기화 성공")
    
    # 캘리브레이션 데이터 로드
    camera_matrix, dist_coeffs = load_calibration_data()
    use_undistort = camera_matrix is not None
    
    # 5x5 ArUco 설정
    aruco_dict, parameters = setup_5x5_aruco()
    
    print("\n🎯 5x5 ArUco 마커 검출 시작")
    if use_undistort:
        print("🔧 왜곡 보정: 활성화")
    else:
        print("� 왜곡 보정: 비활성화")
    print("�📋 조작법:")
    print("   ESC: 종료")
    print("   SPACE: 스크린샷")
    print("   R: 통계 리셋")
    print("   P: 파라미터 조정")
    if use_undistort:
        print("   U: 왜곡 보정 ON/OFF")
    print("")
    
    # 통계 변수
    frame_count = 0
    detection_count = 0
    start_time = time.time()
    marker_stats = {}
    undistort_enabled = use_undistort  # 왜곡 보정 토글용
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ 프레임 읽기 실패")
                continue
            
            frame_count += 1
            
            # 왜곡 보정 적용 (활성화된 경우)
            if use_undistort and undistort_enabled:
                frame = cv.undistort(frame, camera_matrix, dist_coeffs)
            
            # 그레이스케일 변환
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            
            # 5x5 ArUco 마커 검출
            corners, ids, rejected = cv.aruco.detectMarkers(
                gray, aruco_dict, parameters=parameters
            )
            
            detected_this_frame = False
            if ids is not None and len(ids) > 0:
                detection_count += 1
                detected_this_frame = True
                
                # 검출된 마커 그리기
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
                
                # 각 마커 정보 표시
                for i, corner in enumerate(corners):
                    marker_id = ids[i][0]
                    
                    # 마커별 통계
                    if marker_id not in marker_stats:
                        marker_stats[marker_id] = 0
                    marker_stats[marker_id] += 1
                    
                    # 마커 중심점 계산
                    center = np.mean(corner[0], axis=0).astype(int)
                    
                    # 마커 크기 계산
                    marker_size = cv.contourArea(corner[0])
                    
                    # 정보 표시
                    cv.putText(frame, f"ID: {marker_id}", 
                              (center[0] - 30, center[1] - 20), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv.putText(frame, f"Size: {marker_size:.0f}", 
                              (center[0] - 30, center[1] + 10), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                    
                    # 마커 중심점 표시
                    cv.circle(frame, tuple(center), 5, (0, 255, 0), -1)
            
            # 거부된 마커 표시 (디버깅용)
            if rejected is not None and len(rejected) > 0:
                cv.aruco.drawDetectedMarkers(frame, rejected, borderColor=(0, 0, 255))
            
            # 성능 정보 표시
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frame_count / elapsed
                detection_rate = (detection_count / frame_count) * 100
                
                # FPS
                cv.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 검출률
                color = (0, 255, 0) if detection_rate > 30 else (0, 255, 255) if detection_rate > 10 else (0, 0, 255)
                cv.putText(frame, f"Detection: {detection_rate:.1f}%", (10, 60), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # 5x5 딕셔너리 표시
                cv.putText(frame, "5x5_250", (10, 90), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 현재 검출 상태
                status = "DETECTED" if detected_this_frame else "SEARCHING"
                status_color = (0, 255, 0) if detected_this_frame else (0, 165, 255)
                cv.putText(frame, status, (10, 120), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                
                # 왜곡 보정 상태 표시
                if use_undistort:
                    undistort_status = "ON" if undistort_enabled else "OFF"
                    undistort_color = (0, 255, 0) if undistort_enabled else (0, 0, 255)
                    cv.putText(frame, f"Undistort: {undistort_status}", (10, 150), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.6, undistort_color, 2)
            
            # 마커 통계 (우측 상단)
            if marker_stats:
                y_offset = 30
                cv.putText(frame, "Found 5x5 Markers:", (frame.shape[1] - 200, y_offset), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                for marker_id, count in sorted(marker_stats.items()):
                    y_offset += 20
                    percentage = (count / frame_count) * 100
                    cv.putText(frame, f"ID {marker_id}: {count} ({percentage:.1f}%)", 
                              (frame.shape[1] - 200, y_offset), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # 거부된 마커 수 표시
            rejected_count = len(rejected) if rejected is not None else 0
            cv.putText(frame, f"Rejected: {rejected_count}", (10, frame.shape[0] - 40), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # 해상도 정보
            cv.putText(frame, f"{disp_w}x{disp_h}", (10, frame.shape[0] - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv.imshow('5x5 ArUco Detection', frame)
            
            # 키 입력 처리
            key = cv.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                break
            elif key == ord(' '):  # SPACE - 스크린샷
                filename = f"5x5_aruco_capture_{int(time.time())}.jpg"
                cv.imwrite(filename, frame)
                print(f"📸 스크린샷 저장: {filename}")
            elif key == ord('r') or key == ord('R'):  # R - 리셋
                frame_count = 0
                detection_count = 0
                start_time = time.time()
                marker_stats.clear()
                print("🔄 통계 리셋")
            elif key == ord('u') or key == ord('U'):  # U - 왜곡 보정 토글
                if use_undistort:
                    undistort_enabled = not undistort_enabled
                    status = "활성화" if undistort_enabled else "비활성화"
                    print(f"🔧 왜곡 보정: {status}")
                else:
                    print("⚠️ 캘리브레이션 데이터가 없어 왜곡 보정을 사용할 수 없습니다")
            elif key == ord('p') or key == ord('P'):  # P - 파라미터 조정
                adjust_parameters(parameters)
    
    except KeyboardInterrupt:
        print("\n사용자 중단")
    
    finally:
        cap.release()
        cv.destroyAllWindows()
        
        # 최종 결과
        print("\n" + "="*50)
        print("📊 5x5 ArUco 검출 최종 결과")
        print("="*50)
        print(f"총 프레임: {frame_count}")
        print(f"검출 성공: {detection_count}")
        if frame_count > 0:
            print(f"검출률: {(detection_count/frame_count)*100:.1f}%")
            print(f"평균 FPS: {frame_count/elapsed:.1f}")
        
        if marker_stats:
            print("\n검출된 5x5 마커:")
            for marker_id, count in sorted(marker_stats.items()):
                percentage = (count / frame_count) * 100
                print(f"  ID {marker_id}: {count}회 ({percentage:.1f}%)")
        else:
            print("\n❌ 5x5 마커를 찾지 못했습니다.")
            print("💡 확인사항:")
            print("   - 마커가 5x5_250 딕셔너리에 있는지")
            print("   - 마커 크기가 충분한지 (최소 50x50 픽셀)")
            print("   - 조명이 적절한지")
            print("   - 마커가 평평하고 왜곡되지 않았는지")
    
    return True

def adjust_parameters(parameters):
    """실시간 파라미터 조정"""
    print("\n🔧 파라미터 조정 메뉴:")
    print("1. 검출 관대함 증가")
    print("2. 검출 엄격함 증가") 
    print("3. 작은 마커 검출 개선")
    print("4. 기본값 복원")
    
    choice = input("선택 (1-4): ").strip()
    
    if choice == "1":
        # 더 관대한 설정
        parameters.minMarkerPerimeterRate = 0.01
        parameters.maxMarkerPerimeterRate = 6.0
        parameters.polygonalApproxAccuracyRate = 0.05
        parameters.minCornerDistanceRate = 0.03
        print("✅ 관대한 검출 모드")
    
    elif choice == "2":
        # 더 엄격한 설정
        parameters.minMarkerPerimeterRate = 0.05
        parameters.maxMarkerPerimeterRate = 3.0
        parameters.polygonalApproxAccuracyRate = 0.02
        parameters.minCornerDistanceRate = 0.08
        print("✅ 엄격한 검출 모드")
    
    elif choice == "3":
        # 작은 마커 검출 개선
        parameters.minMarkerPerimeterRate = 0.005
        parameters.adaptiveThreshWinSizeMin = 3
        parameters.adaptiveThreshWinSizeMax = 15
        print("✅ 작은 마커 검출 모드")
    
    elif choice == "4":
        # 기본값 복원
        parameters.minMarkerPerimeterRate = 0.03
        parameters.maxMarkerPerimeterRate = 4.0
        parameters.polygonalApproxAccuracyRate = 0.03
        parameters.minCornerDistanceRate = 0.05
        print("✅ 기본값 복원")

def test_5x5_dictionary_variants():
    """5x5 딕셔너리 변형들 테스트"""
    print("=== 5x5 딕셔너리 변형 테스트 ===")
    
    variants = [
        (cv.aruco.DICT_5X5_50, "5X5_50 (50개 마커)"),
        (cv.aruco.DICT_5X5_100, "5X5_100 (100개 마커)"),
        (cv.aruco.DICT_5X5_250, "5X5_250 (250개 마커)"),
    ]
    
    pipeline = gstreamer_pipeline(640, 480, 640, 480, 30, 0)
    cap = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    
    if not cap.isOpened():
        cap = cv.VideoCapture(0)
        if not cap.isOpened():
            print("❌ 카메라 실패")
            return
    
    print("📹 각 5x5 딕셔너리 변형으로 5초씩 테스트")
    print("ESC: 다음 딕셔너리로")
    
    for dict_type, dict_name in variants:
        print(f"\n🔍 테스트 중: {dict_name}")
        
        aruco_dict = cv.aruco.Dictionary_get(dict_type)
        parameters = cv.aruco.DetectorParameters_create()
        
        # 5x5에 최적화된 기본 설정
        parameters.minMarkerPerimeterRate = 0.03
        parameters.maxMarkerPerimeterRate = 4.0
        
        detection_count = 0
        frame_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 5:  # 5초간 테스트
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, _ = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
            
            if ids is not None:
                detection_count += 1
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
            
            # 현재 딕셔너리 표시
            cv.putText(frame, dict_name, (10, 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if frame_count > 0:
                detection_rate = (detection_count / frame_count) * 100
                cv.putText(frame, f"Detection: {detection_rate:.1f}%", (10, 60), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv.imshow('5x5 Dictionary Test', frame)
            
            if cv.waitKey(1) & 0xFF == 27:  # ESC로 다음 딕셔너리
                break
        
        if frame_count > 0:
            final_rate = (detection_count / frame_count) * 100
            print(f"   결과: {final_rate:.1f}% 검출률 ({detection_count}/{frame_count})")
        else:
            print("   결과: 테스트 실패")
    
    cap.release()
    cv.destroyAllWindows()

def main():
    """메인 함수"""
    print("=== 5x5 ArUco 마커 전용 검출 시스템 ===")
    print("1. 5x5 ArUco 검출 실행")
    print("2. 5x5 딕셔너리 변형 테스트")
    print("3. 전체 실행")
    
    choice = input("선택하세요 (1-3): ").strip()
    
    if choice == "1":
        run_5x5_aruco_detection()
    elif choice == "2":
        test_5x5_dictionary_variants()
    elif choice == "3":
        test_5x5_dictionary_variants()
        print("\n5초 후 메인 검출 시작...")
        time.sleep(5)
        run_5x5_aruco_detection()
    else:
        print("메인 검출을 실행합니다.")
        run_5x5_aruco_detection()

if __name__ == "__main__":
    main()
