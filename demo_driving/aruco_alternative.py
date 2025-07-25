"""
ArUco 대체 솔루션 - 즉시 사용 가능

문제: OpenCV 4.6.0에서 cv.aruco.detectMarkers() Segmentation fault
해결: 색상 기반 마커 시스템으로 완전 대체

장점:
- ArUco보다 더 빠름 (실시간 처리)
- 더 안정적 (크래시 없음)
- 더 간단한 마커 제작
- 커스터마이징 용이

사용법:
"""

import cv2 as cv
import numpy as np
from driving import move_forward, turn_left, turn_right, move_stop, move_backward

class ArUcoAlternative:
    """ArUco 완전 대체 시스템"""
    
    def __init__(self):
        print("🔄 ArUco 대체 시스템 초기화")
        print("   OpenCV 4.6.0 ArUco 버그 회피")
        
        # 색상 범위 (HSV)
        self.markers = {
            0: {'name': '정지', 'color': 'red', 'action': 'stop'},
            1: {'name': '전진', 'color': 'green', 'action': 'forward'},  
            2: {'name': '후진', 'color': 'blue', 'action': 'backward'},
            3: {'name': '좌회전', 'color': 'yellow', 'action': 'left'},
            4: {'name': '우회전', 'color': 'purple', 'action': 'right'}
        }
        
        self.color_ranges = {
            'red': [(np.array([0, 120, 70]), np.array([10, 255, 255])),
                   (np.array([170, 120, 70]), np.array([180, 255, 255]))],
            'green': [(np.array([40, 50, 50]), np.array([80, 255, 255]))],
            'blue': [(np.array([100, 50, 50]), np.array([130, 255, 255]))],
            'yellow': [(np.array([20, 100, 100]), np.array([30, 255, 255]))],
            'purple': [(np.array([130, 50, 50]), np.array([160, 255, 255]))]
        }
    
    def detect_markers(self, frame):
        """ArUco.detectMarkers() 대체 함수"""
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        detected_markers = []
        
        for marker_id, marker_info in self.markers.items():
            color = marker_info['color']
            
            # 색상 마스크 생성
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in self.color_ranges[color]:
                mask += cv.inRange(hsv, lower, upper)
            
            # 노이즈 제거
            kernel = np.ones((5,5), np.uint8)
            mask = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)
            mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, kernel)
            
            # 윤곽선 찾기
            contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv.contourArea(contour)
                if area > 1000:  # 최소 크기
                    # 경계 박스
                    x, y, w, h = cv.boundingRect(contour)
                    aspect_ratio = float(w) / h
                    
                    if 0.5 <= aspect_ratio <= 2.0:  # 합리적 비율
                        center = (x + w//2, y + h//2)
                        
                        # ArUco 형식으로 반환
                        corners = np.array([[
                            [x, y], [x+w, y], [x+w, y+h], [x, y+h]
                        ]], dtype=np.float32)
                        
                        detected_markers.append({
                            'id': marker_id,
                            'corners': corners,
                            'center': center,
                            'area': area,
                            'action': marker_info['action']
                        })
        
        # ArUco 호환 형식으로 반환
        if detected_markers:
            corners = [m['corners'] for m in detected_markers]
            ids = np.array([[m['id']] for m in detected_markers])
            return corners, ids, detected_markers
        else:
            return None, None, []
    
    def draw_detected_markers(self, frame, corners, ids):
        """ArUco.drawDetectedMarkers() 대체 함수"""
        if ids is not None:
            for i, marker_id in enumerate(ids):
                marker_id = marker_id[0]
                corner = corners[i][0].astype(int)
                
                # 마커 경계 그리기
                cv.polylines(frame, [corner], True, (0, 255, 0), 2)
                
                # ID와 이름 표시
                center = tuple(corner.mean(axis=0).astype(int))
                marker_name = self.markers[marker_id]['name']
                
                cv.putText(frame, f"ID:{marker_id}", 
                          (center[0] - 20, center[1] - 20),
                          cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv.putText(frame, marker_name, 
                          (center[0] - 20, center[1] + 20),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        
        return frame
    
    def control_robot(self, marker_data):
        """마커 기반 로봇 제어"""
        if not marker_data:
            move_stop()
            return
        
        # 가장 큰 마커 사용
        main_marker = max(marker_data, key=lambda x: x['area'])
        action = main_marker['action']
        
        if action == 'stop':
            move_stop()
            print("🛑 정지")
        elif action == 'forward':
            move_forward()
            print("⬆️ 전진")
        elif action == 'backward':
            move_backward()
            print("⬇️ 후진")
        elif action == 'left':
            turn_left()
            print("⬅️ 좌회전")
        elif action == 'right':
            turn_right()
            print("➡️ 우회전")

def start_aruco_alternative():
    """ArUco 대체 시스템 시작"""
    detector = ArUcoAlternative()
    
    print("🚀 ArUco 대체 시스템 시작")
    print("마커 종류:")
    for mid, info in detector.markers.items():
        print(f"   ID {mid}: {info['color']} - {info['name']}")
    print("ESC로 종료")
    
    try:
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("❌ 카메라 열기 실패")
            return
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 마커 탐지 (ArUco 대체)
            corners, ids, marker_data = detector.detect_markers(frame)
            
            # 마커 표시 (ArUco 대체)
            frame = detector.draw_detected_markers(frame, corners, ids)
            
            # 로봇 제어
            detector.control_robot(marker_data)
            
            # 상태 표시
            status = f"Markers: {len(marker_data)}"
            cv.putText(frame, status, (10, 30),
                      cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv.imshow('ArUco Alternative', frame)
            
            if cv.waitKey(1) & 0xFF == 27:  # ESC
                break
    
    except Exception as e:
        print(f"오류: {e}")
    finally:
        try:
            cap.release()
            cv.destroyAllWindows()
            move_stop()
        except:
            pass

if __name__ == "__main__":
    start_aruco_alternative()
