import cv2 as cv
import numpy as np

def detect_color_markers(frame):
    """색상 기반 마커 탐지 (ArUco 대신)"""
    
    # HSV로 변환
    hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    
    # 빨간색 범위 (마커용)
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])
    
    # 빨간색 마스크
    mask1 = cv.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv.inRange(hsv, lower_red2, upper_red2)
    red_mask = mask1 + mask2
    
    # 노이즈 제거
    kernel = np.ones((5,5), np.uint8)
    red_mask = cv.morphologyEx(red_mask, cv.MORPH_OPEN, kernel)
    red_mask = cv.morphologyEx(red_mask, cv.MORPH_CLOSE, kernel)
    
    # 윤곽선 찾기
    contours, _ = cv.findContours(red_mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    
    markers = []
    for contour in contours:
        area = cv.contourArea(contour)
        if area > 1000:  # 최소 크기
            # 경계 박스
            x, y, w, h = cv.boundingRect(contour)
            
            # 정사각형에 가까운지 확인
            aspect_ratio = float(w) / h
            if 0.7 <= aspect_ratio <= 1.3:  # 정사각형에 가까움
                markers.append({
                    'center': (x + w//2, y + h//2),
                    'size': (w, h),
                    'area': area,
                    'contour': contour
                })
    
    return markers

def alternative_navigation():
    """ArUco 없이 색상 마커로 네비게이션"""
    print("=== 색상 마커 네비게이션 테스트 ===")
    
    try:
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("카메라 열기 실패")
            return False
        
        print("카메라 열기 성공")
        print("빨간색 정사각형 마커를 카메라 앞에 두세요")
        print("ESC로 종료")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 마커 탐지
            markers = detect_color_markers(frame)
            
            # 마커 표시
            for i, marker in enumerate(markers):
                center = marker['center']
                size = marker['size']
                
                # 중심점 표시
                cv.circle(frame, center, 5, (0, 255, 0), -1)
                
                # 박스 그리기
                x = center[0] - size[0]//2
                y = center[1] - size[1]//2
                cv.rectangle(frame, (x, y), (x + size[0], y + size[1]), (0, 255, 0), 2)
                
                # ID 표시
                cv.putText(frame, f"Marker {i}", (center[0] - 30, center[1] - 20),
                          cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # 거리 계산 (간단한 방법)
                distance_estimate = 10000 / marker['area']  # 대략적인 거리
                cv.putText(frame, f"Dist: {distance_estimate:.1f}", 
                          (center[0] - 30, center[1] + 20),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            # 상태 표시
            cv.putText(frame, f"Markers: {len(markers)}", (10, 30),
                      cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv.imshow("Color Marker Navigation", frame)
            
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
        
        return True
        
    except Exception as e:
        print(f"색상 마커 테스트 중 오류: {e}")
        return False
    finally:
        try:
            cap.release()
            cv.destroyAllWindows()
        except:
            pass

if __name__ == "__main__":
    alternative_navigation()
