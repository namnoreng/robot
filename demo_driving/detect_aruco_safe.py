import cv2 as cv
import numpy as np
from driving import move_forward, turn_left, turn_right, move_stop, move_backward
from default_setting import robot, connection, camera_back
import json

class SimpleMarkerDetector:
    """ArUco 대신 사용할 간단한 마커 탐지 시스템"""
    
    def __init__(self):
        # 색상 기반 마커 설정
        self.color_ranges = {
            'red': {
                'lower1': np.array([0, 120, 70]),
                'upper1': np.array([10, 255, 255]),
                'lower2': np.array([170, 120, 70]),
                'upper2': np.array([180, 255, 255])
            },
            'green': {
                'lower': np.array([40, 50, 50]),
                'upper': np.array([80, 255, 255])
            },
            'blue': {
                'lower': np.array([100, 50, 50]),
                'upper': np.array([130, 255, 255])
            }
        }
        
        # 마커 ID 매핑
        self.marker_ids = {
            ('red',): 0,
            ('green',): 1,
            ('blue',): 2,
            ('red', 'green'): 3,
            ('red', 'blue'): 4,
            ('green', 'blue'): 5
        }
    
    def detect_color_regions(self, frame, color_name):
        """특정 색상 영역 탐지"""
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        
        if color_name == 'red':
            mask1 = cv.inRange(hsv, self.color_ranges['red']['lower1'], self.color_ranges['red']['upper1'])
            mask2 = cv.inRange(hsv, self.color_ranges['red']['lower2'], self.color_ranges['red']['upper2'])
            mask = mask1 + mask2
        else:
            mask = cv.inRange(hsv, self.color_ranges[color_name]['lower'], self.color_ranges[color_name]['upper'])
        
        # 노이즈 제거
        kernel = np.ones((5,5), np.uint8)
        mask = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)
        mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, kernel)
        
        # 윤곽선 찾기
        contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            area = cv.contourArea(contour)
            if area > 500:
                x, y, w, h = cv.boundingRect(contour)
                aspect_ratio = float(w) / h
                if 0.5 <= aspect_ratio <= 2.0:
                    regions.append({
                        'center': (x + w//2, y + h//2),
                        'size': (w, h),
                        'area': area,
                        'bbox': (x, y, w, h)
                    })
        
        return regions
    
    def detect_markers(self, frame):
        """마커 탐지"""
        markers = []
        
        # 각 색상별로 영역 탐지
        color_detections = {}
        for color in ['red', 'green', 'blue']:
            color_detections[color] = self.detect_color_regions(frame, color)
        
        # 근처 색상들을 조합해서 마커 ID 결정
        all_regions = []
        for color, regions in color_detections.items():
            for region in regions:
                region['color'] = color
                all_regions.append(region)
        
        # 거리 기반으로 마커 그룹화
        processed = set()
        for i, region1 in enumerate(all_regions):
            if i in processed:
                continue
            
            nearby_colors = [region1['color']]
            nearby_regions = [region1]
            
            for j, region2 in enumerate(all_regions):
                if i != j and j not in processed:
                    dist = np.sqrt((region1['center'][0] - region2['center'][0])**2 + 
                                 (region1['center'][1] - region2['center'][1])**2)
                    
                    if dist < 100:
                        nearby_colors.append(region2['color'])
                        nearby_regions.append(region2)
                        processed.add(j)
            
            processed.add(i)
            
            # 색상 조합으로 마커 ID 결정
            color_tuple = tuple(sorted(set(nearby_colors)))
            marker_id = self.marker_ids.get(color_tuple, -1)
            
            if marker_id >= 0:
                center_x = int(np.mean([r['center'][0] for r in nearby_regions]))
                center_y = int(np.mean([r['center'][1] for r in nearby_regions]))
                total_area = sum([r['area'] for r in nearby_regions])
                
                markers.append({
                    'id': marker_id,
                    'center': (center_x, center_y),
                    'area': total_area,
                    'colors': nearby_colors,
                    'regions': nearby_regions
                })
        
        return markers

def control_robot_with_marker(marker_id, center_x, center_y, frame_width):
    """마커 기반 로봇 제어"""
    frame_center = frame_width // 2
    
    # 마커 위치에 따른 제어
    if marker_id == 0:  # 빨간색 - 정지
        move_stop()
        print("빨간색 마커: 정지")
    elif marker_id == 1:  # 초록색 - 전진
        if abs(center_x - frame_center) < 50:  # 중앙 근처
            move_forward()
            print("초록색 마커: 전진")
        elif center_x < frame_center:  # 왼쪽
            turn_left()
            print("초록색 마커: 좌회전")
        else:  # 오른쪽
            turn_right()
            print("초록색 마커: 우회전")
    elif marker_id == 2:  # 파란색 - 후진
        move_backward()
        print("파란색 마커: 후진")

def start_detecting_aruco():
    """간단한 마커 탐지 및 로봇 제어 (ArUco 대체)"""
    
    try:
        detector = SimpleMarkerDetector()
        
        print("간단한 마커 탐지 시작")
        print("마커 종류:")
        print("ID 0 (빨강): 정지")
        print("ID 1 (초록): 전진/회전")
        print("ID 2 (파랑): 후진")
        print("ID 3 (빨강+초록): 복합 동작")
        print("ID 4 (빨강+파랑): 복합 동작")
        print("ID 5 (초록+파랑): 복합 동작")
        print("ESC를 눌러 종료")
        
        while True:
            ret, frame = robot.read()
            if not ret:
                print("프레임 읽기 실패")
                break
            
            # 마커 탐지
            markers = detector.detect_markers(frame)
            
            # 마커가 탐지되면 표시 및 제어
            if markers:
                for marker in markers:
                    center = marker['center']
                    marker_id = marker['id']
                    
                    # 마커 표시
                    cv.circle(frame, center, 8, (0, 255, 255), -1)
                    cv.putText(frame, f"ID:{marker_id}", (center[0] - 20, center[1] - 20),
                              cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    
                    # 거리 표시
                    distance = 15000 / marker['area'] if marker['area'] > 0 else 0
                    cv.putText(frame, f"{distance:.1f}cm", (center[0] - 30, center[1] + 30),
                              cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    # 각 색상 영역 표시
                    for region in marker['regions']:
                        x, y, w, h = region['bbox']
                        color_map = {'red': (0, 0, 255), 'green': (0, 255, 0), 'blue': (255, 0, 0)}
                        color = color_map.get(region['color'], (255, 255, 255))
                        cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    
                    # 로봇 제어 로직
                    control_robot_with_marker(marker_id, center[0], center[1], frame.shape[1])
            else:
                # 마커가 없으면 정지
                move_stop()
            
            # 상태 정보 표시
            cv.putText(frame, f"Markers: {len(markers)}", (10, 30),
                      cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # 탐지된 마커 정보 표시
            if markers:
                marker_info = ", ".join([f"ID{m['id']}" for m in markers])
                cv.putText(frame, marker_info, (10, 70),
                          cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # 화면 표시
            cv.imshow('Simple Marker Detection', frame)
            
            # ESC 키로 종료
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
    
    except Exception as e:
        print(f"마커 탐지 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            cv.destroyAllWindows()
            move_stop()
        except:
            pass

# 호환성을 위한 함수 (기존 코드에서 호출할 수 있도록)
def start_detecting_aruco_old(cap, marker_dict, param_markers):
    """기존 함수와의 호환성을 위한 래퍼"""
    print("⚠️  ArUco 함수가 호출되었지만, 안전을 위해 색상 마커 시스템을 사용합니다.")
    start_detecting_aruco()

if __name__ == "__main__":
    start_detecting_aruco()
