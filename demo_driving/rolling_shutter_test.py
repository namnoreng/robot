import cv2 as cv
import numpy as np
import time
import platform
from cv2 import aruco

current_platform = platform.system()

def test_rolling_shutter_settings():
    """Rolling Shutter 효과를 테스트하는 함수"""
    
    print("=== Rolling Shutter 테스트 시작 ===")
    print("빠른 움직임으로 Rolling Shutter 효과를 확인하세요")
    print("키 조작:")
    print("  's': 현재 설정 저장")
    print("  '1': 기본 설정")
    print("  '2': Rolling Shutter 최소화 설정 1")
    print("  '3': Rolling Shutter 최소화 설정 2")
    print("  '4': 고속 촬영 설정")
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
    
    # ArUco 설정
    marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
    
    # 기본 해상도 설정
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv.CAP_PROP_FPS, 30)
    
    current_setting = "기본 설정"
    frame_count = 0
    fps_timer = time.time()
    fps_display = 0
    
    # 설정별 함수들
    def apply_basic_setting():
        """기본 카메라 설정"""
        try:
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.75)  # 자동 노출
            cap.set(cv.CAP_PROP_EXPOSURE, -6)
            cap.set(cv.CAP_PROP_GAIN, 10)
            cap.set(cv.CAP_PROP_BRIGHTNESS, 128)
            cap.set(cv.CAP_PROP_CONTRAST, 128)
            cap.set(cv.CAP_PROP_FPS, 30)
            return "기본 설정"
        except Exception as e:
            print(f"기본 설정 실패: {e}")
            return "설정 실패"
    
    def apply_rolling_shutter_fix_1():
        """Rolling Shutter 최소화 설정 1 - 짧은 노출"""
        try:
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 수동 노출 모드
            cap.set(cv.CAP_PROP_EXPOSURE, -8)         # 매우 짧은 노출
            cap.set(cv.CAP_PROP_GAIN, 40)             # 게인 증가로 밝기 보상
            cap.set(cv.CAP_PROP_BRIGHTNESS, 140)      # 밝기 증가
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
            cap.set(cv.CAP_PROP_FPS, 60)              # 60fps
            cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 수동 노출
            cap.set(cv.CAP_PROP_EXPOSURE, -7)         # 짧은 노출
            cap.set(cv.CAP_PROP_GAIN, 50)             # 중간 게인
            cap.set(cv.CAP_PROP_BRIGHTNESS, 150)      # 높은 밝기
            cap.set(cv.CAP_PROP_CONTRAST, 140)        # 높은 대비
            # 해상도를 낮춰서 60fps 지원
            cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, 360)
            return "고속 촬영 설정 (60fps, 640x360)"
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
        
        # ArUco 마커 검출
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        corners, ids, _ = aruco.detectMarkers(gray, marker_dict, parameters=param_markers)
        
        # 마커가 검출되면 표시
        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            for i, marker_id in enumerate(ids.flatten()):
                center_x = int(corners[i][0][:, 0].mean())
                center_y = int(corners[i][0][:, 1].mean())
                cv.putText(frame, f"ID: {marker_id}", 
                          (center_x - 30, center_y - 10), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 정보 표시
        cv.putText(frame, f"Setting: {current_setting}", 
                  (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv.putText(frame, f"FPS: {fps_display}", 
                  (10, 60), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv.putText(frame, f"Resolution: {int(cap.get(cv.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))}", 
                  (10, 90), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 사용법 표시 (화면 하단)
        cv.putText(frame, "Fast motion test - Press 1,2,3,4 for settings, s:save, r:reset, q:quit", 
                  (10, frame.shape[0] - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # 화면 표시
        cv.imshow('Rolling Shutter Test', frame)
        
        # 키 입력 처리
        key = cv.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("테스트 종료")
            break
        elif key == ord('s'):
            save_current_frame(frame, current_setting.replace(" ", "_"))
        elif key == ord('1'):
            current_setting = apply_basic_setting()
            print(f"✅ {current_setting} 적용")
        elif key == ord('2'):
            current_setting = apply_rolling_shutter_fix_1()
            print(f"✅ {current_setting} 적용")
        elif key == ord('3'):
            current_setting = apply_rolling_shutter_fix_2()
            print(f"✅ {current_setting} 적용")
        elif key == ord('4'):
            current_setting = apply_high_speed_setting()
            print(f"✅ {current_setting} 적용")
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
