#!/usr/bin/env python3
"""
CSI 카메라 5x5 ArUco 마커 전용 인식 시스템 + 거리 측정
간단하고 최적화된 5x5 전용 검출기 with Distance Calculation
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
            print("✅ 캘리브레이션 데이터 로드 성공 - 왜곡 보정 & 거리 측정 활성화")
            return camera_matrix, dist_coeffs
        except Exception as e:
            print(f"⚠️ 캘리브레이션 로드 실패: {e}")
    else:
        print("⚠️ 캘리브레이션 파일 없음 - 왜곡 보정 & 거리 측정 비활성화")
    
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

def calculate_marker_distance(corners, camera_matrix, dist_coeffs, marker_size_m=0.05):
    """
    ArUco 마커와의 거리 계산
    
    Args:
        corners: 마커 코너 좌표
        camera_matrix: 카메라 매트릭스
        dist_coeffs: 왜곡 계수
        marker_size_m: 실제 마커 크기 (미터 단위, 기본값: 5cm)
    
    Returns:
        distance: 거리 (미터), None if calculation fails
        tvec: 변환 벡터
        rvec: 회전 벡터
    """
    if camera_matrix is None or dist_coeffs is None:
        return None, None, None
    
    try:
        # 3D 마커 좌표 (정사각형, Z=0 평면)
        marker_3d_points = np.array([
            [-marker_size_m/2, marker_size_m/2, 0],    # 좌상
            [marker_size_m/2, marker_size_m/2, 0],     # 우상  
            [marker_size_m/2, -marker_size_m/2, 0],    # 우하
            [-marker_size_m/2, -marker_size_m/2, 0]    # 좌하
        ], dtype=np.float32)
        
        # 2D 이미지 좌표
        marker_2d_points = corners[0].astype(np.float32)
        
        # PnP 문제 해결하여 포즈 추정
        success, rvec, tvec = cv.solvePnP(
            marker_3d_points, marker_2d_points, 
            camera_matrix, dist_coeffs
        )
        
        if success:
            # 거리는 변환 벡터의 크기 (유클리드 거리)
            distance = np.linalg.norm(tvec)
            return distance, tvec, rvec
        else:
            return None, None, None
            
    except Exception as e:
        print(f"거리 계산 오류: {e}")
        return None, None, None

def draw_distance_info(frame, corners, distance, tvec, rvec, marker_id, camera_matrix, dist_coeffs):
    """마커에 거리 정보와 좌표축 그리기"""
    if distance is None:
        return
    
    try:
        # 마커 중심점 계산
        center = np.mean(corners[0], axis=0).astype(int)
        
        # 거리 텍스트 표시
        distance_cm = distance * 100  # 미터를 센티미터로 변환
        cv.putText(frame, f"ID{marker_id}: {distance_cm:.1f}cm", 
                  (center[0] - 60, center[1] - 30), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # X, Y, Z 좌표 표시 (tvec는 카메라 좌표계)
        x, y, z = tvec.flatten() * 100  # 센티미터로 변환
        cv.putText(frame, f"X:{x:.1f} Y:{y:.1f} Z:{z:.1f}", 
                  (center[0] - 80, center[1] + 20), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
        
        # 3D 좌표축 그리기
        if camera_matrix is not None and dist_coeffs is not None:
            axis_length = 0.02  # 2cm 길이의 축
            axis_3d = np.array([
                [0, 0, 0],           # 원점
                [axis_length, 0, 0], # X축 (빨강)
                [0, axis_length, 0], # Y축 (초록)  
                [0, 0, -axis_length] # Z축 (파랑, 카메라 쪽으로)
            ], dtype=np.float32)
            
            # 3D 축을 2D로 투영
            axis_2d, _ = cv.projectPoints(axis_3d, rvec, tvec, camera_matrix, dist_coeffs)
            axis_2d = axis_2d.astype(int)
            
            # 좌표축 그리기
            origin = tuple(axis_2d[0].ravel())
            x_axis = tuple(axis_2d[1].ravel())
            y_axis = tuple(axis_2d[2].ravel()) 
            z_axis = tuple(axis_2d[3].ravel())
            
            # X축 (빨강), Y축 (초록), Z축 (파랑)
            cv.line(frame, origin, x_axis, (0, 0, 255), 3)  # X축
            cv.line(frame, origin, y_axis, (0, 255, 0), 3)  # Y축  
            cv.line(frame, origin, z_axis, (255, 0, 0), 3)  # Z축
            
    except Exception as e:
        print(f"거리 정보 그리기 오류: {e}")

def run_5x5_aruco_detection():
    """5x5 ArUco 마커 검출 및 거리 측정 실행"""
    print("=== 5x5 ArUco 마커 전용 검출 + 거리 측정 시스템 ===")
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
    
    # ArUco 마커 실제 크기 설정
    print("\n📏 ArUco 마커 실제 크기를 입력하세요:")
    print("1. 5cm (기본값)")
    print("2. 3cm")
    print("3. 직접 입력")
    
    marker_choice = input("선택 (1-3): ").strip()
    
    if marker_choice == "2":
        marker_size_m = 0.03  # 3cm
        print("✅ 마커 크기: 3cm")
    elif marker_choice == "3":
        try:
            size_cm = float(input("마커 크기 (cm): "))
            marker_size_m = size_cm / 100.0  # cm를 m로 변환
            print(f"✅ 마커 크기: {size_cm}cm")
        except ValueError:
            marker_size_m = 0.05  # 기본값
            print("⚠️ 잘못된 입력, 기본값 5cm 사용")
    else:
        marker_size_m = 0.05  # 5cm (기본값)
        print("✅ 마커 크기: 5cm")
    
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
    
    print("\n🎯 5x5 ArUco 마커 검출 및 거리 측정 시작")
    if use_undistort:
        print("🔧 왜곡 보정: 활성화")
        print(f"📏 마커 크기: {marker_size_m*100:.1f}cm")
        print("📐 거리 측정: 활성화")
    else:
        print("🔧 왜곡 보정: 비활성화")
        print("📐 거리 측정: 비활성화 (캘리브레이션 필요)")
    print("📋 조작법:")
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
                    
                    # 거리 계산 (캘리브레이션이 있는 경우)
                    if use_undistort and camera_matrix is not None:
                        distance, tvec, rvec = calculate_marker_distance(
                            [corner], camera_matrix, dist_coeffs, marker_size_m=marker_size_m
                        )
                        # 거리 정보와 좌표축 그리기
                        draw_distance_info(frame, [corner], distance, tvec, rvec, 
                                         marker_id, camera_matrix, dist_coeffs)
                    else:
                        # 캘리브레이션이 없으면 기본 정보만 표시
                        center = np.mean(corner[0], axis=0).astype(int)
                        marker_size = cv.contourArea(corner[0])
                        
                        cv.putText(frame, f"ID: {marker_id}", 
                                  (center[0] - 30, center[1] - 20), 
                                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        cv.putText(frame, f"Size: {marker_size:.0f}", 
                                  (center[0] - 30, center[1] + 10), 
                                  cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
            
            # 정보 표시 (프레임당 5번에 한 번)
            if frame_count % 5 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                detection_rate = (detection_count / frame_count) * 100
                
                # FPS
                cv.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 검출률
                cv.putText(frame, f"Detection: {detection_rate:.1f}%", (10, 60), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
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
                
                total_detections = sum(marker_stats.values())
                for marker_id, count in sorted(marker_stats.items()):
                    y_offset += 25
                    percentage = (count / total_detections) * 100
                    cv.putText(frame, f"ID {marker_id}: {count} ({percentage:.1f}%)", 
                              (frame.shape[1] - 200, y_offset), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # 기타 정보 (하단)
            rejected_count = len(rejected) if rejected is not None else 0
            cv.putText(frame, f"Rejected: {rejected_count}", (10, frame.shape[0] - 40), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
            
            # 해상도 표시
            cv.putText(frame, f"{disp_w}x{disp_h}", (10, frame.shape[0] - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
            
            cv.imshow('5x5 ArUco Detection + Distance', frame)
            
            # 키 입력 처리
            key = cv.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                break
            elif key == ord(' '):  # SPACE - 스크린샷
                filename = f"5x5_aruco_distance_capture_{int(time.time())}.jpg"
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
    
    except KeyboardInterrupt:
        print("\n사용자 중단")
    
    finally:
        cap.release()
        cv.destroyAllWindows()
        
        # 최종 결과
        if frame_count > 0:
            elapsed = time.time() - start_time
            print(f"\n📊 최종 결과:")
            print(f"총 프레임: {frame_count}")
            print(f"검출 프레임: {detection_count}")
            print(f"검출률: {(detection_count/frame_count)*100:.1f}%")
            print(f"평균 FPS: {frame_count/elapsed:.1f}")
            
            if marker_stats:
                print(f"\n📈 마커별 검출 통계:")
                total = sum(marker_stats.values())
                for marker_id, count in sorted(marker_stats.items()):
                    percentage = (count / total) * 100
                    print(f"  ID {marker_id}: {count}회 ({percentage:.1f}%)")
    
    return True

if __name__ == "__main__":
    run_5x5_aruco_detection()
