import cv2 as cv
import numpy as np
import time
import platform
from cv2 import aruco

current_platform = platform.system()

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
    
    # 카메라 초기화
    if current_platform == 'Windows':
        cap = cv.VideoCapture(0, cv.CAP_DSHOW)
    elif current_platform == 'Linux':
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
    else:
        cap = cv.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return
    
    # ArUco 설정 - 성능 최적화
    marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
    
    # ArUco 검출 성능 최적화
    param_markers.adaptiveThreshWinSizeMin = 5
    param_markers.adaptiveThreshWinSizeMax = 15  # 더 작은 윈도우
    param_markers.adaptiveThreshWinSizeStep = 5
    param_markers.minMarkerPerimeterRate = 0.05
    param_markers.maxMarkerPerimeterRate = 2.0  # 더 작은 범위
    param_markers.polygonalApproxAccuracyRate = 0.05
    
    # 기본 해상도 설정 - 성능 우선
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv.CAP_PROP_FPS, 30)
    cap.set(cv.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 최소화
    
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
        
        # ArUco 마커 검출 - 프레임 스킵으로 성능 최적화
        aruco_skip_counter += 1
        if aruco_skip_counter % (ARUCO_SKIP_FRAMES + 1) == 0:
            # 실제 ArUco 검출 수행
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, _ = aruco.detectMarkers(gray, marker_dict, parameters=param_markers)
            last_ids = ids
            last_corners = corners
        else:
            # 이전 검출 결과 재사용
            ids = last_ids
            corners = last_corners
        
        # 마커가 검출되면 표시 (간소화)
        if ids is not None and corners is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            # 첫 번째 마커만 ID 표시 (성능 향상)
            if len(ids) > 0:
                marker_id = ids[0][0]
                center_x = int(corners[0][0][:, 0].mean())
                center_y = int(corners[0][0][:, 1].mean())
                cv.putText(frame, f"ID: {marker_id}", 
                          (center_x - 30, center_y - 10), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 정보 표시 (간소화)
        cv.putText(frame, f"FPS: {fps_display}", 
                  (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv.putText(frame, f"{current_setting}", 
                  (10, 60), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 사용법 표시 (간소화)
        cv.putText(frame, "1,2,3,4,5:settings s:save q:quit", 
                  (10, frame.shape[0] - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
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
    test_rolling_shutter_settings()
