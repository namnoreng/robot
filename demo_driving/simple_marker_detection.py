import cv2 as cv
import numpy as np
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
        
        # 마커 ID 매핑 (색상 조합으로 ID 구분)
        self.marker_ids = {
            ('red',): 0,           # 빨간색만 = ID 0
            ('green',): 1,         # 초록색만 = ID 1  
            ('blue',): 2,          # 파란색만 = ID 2
            ('red', 'green'): 3,   # 빨강+초록 = ID 3
            ('red', 'blue'): 4,    # 빨강+파랑 = ID 4
            ('green', 'blue'): 5   # 초록+파랑 = ID 5
        }
    
    def detect_color_regions(self, frame, color_name):
        """특정 색상 영역 탐지"""
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        
        if color_name == 'red':
            # 빨간색은 HSV에서 두 범위로 나뉨
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
            if area > 500:  # 최소 크기
                x, y, w, h = cv.boundingRect(contour)
                aspect_ratio = float(w) / h
                if 0.5 <= aspect_ratio <= 2.0:  # 합리적인 비율
                    regions.append({
                        'center': (x + w//2, y + h//2),
                        'size': (w, h),
                        'area': area,
                        'bbox': (x, y, w, h)
                    })
        
        return regions
    
    def detect_markers(self, frame):
        """마커 탐지 (ArUco 대체)"""
        markers = []
        
        # 각 색상별로 영역 탐지
        color_detections = {}
        for color in ['red', 'green', 'blue']:
            color_detections[color] = self.detect_color_regions(frame, color)
        
        # 근처에 있는 색상들을 조합해서 마커 ID 결정
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
            
            # 현재 영역과 가까운 다른 색상 영역들 찾기
            nearby_colors = [region1['color']]
            nearby_regions = [region1]
            
            for j, region2 in enumerate(all_regions):
                if i != j and j not in processed:
                    # 두 영역 간 거리 계산
                    dist = np.sqrt((region1['center'][0] - region2['center'][0])**2 + 
                                 (region1['center'][1] - region2['center'][1])**2)
                    
                    if dist < 100:  # 100픽셀 내에 있으면 같은 마커로 간주
                        nearby_colors.append(region2['color'])
                        nearby_regions.append(region2)
                        processed.add(j)
            
            processed.add(i)
            
            # 색상 조합으로 마커 ID 결정
            color_tuple = tuple(sorted(set(nearby_colors)))
            marker_id = self.marker_ids.get(color_tuple, -1)
            
            if marker_id >= 0:
                # 마커의 중심점 계산 (모든 영역의 평균)
                center_x = int(np.mean([r['center'][0] for r in nearby_regions]))
                center_y = int(np.mean([r['center'][1] for r in nearby_regions]))
                
                # 마커 크기 계산
                total_area = sum([r['area'] for r in nearby_regions])
                
                markers.append({
                    'id': marker_id,
                    'center': (center_x, center_y),
                    'area': total_area,
                    'colors': nearby_colors,
                    'regions': nearby_regions
                })
        
        return markers
    
    def draw_markers(self, frame, markers):
        """마커 표시 (ArUco drawDetectedMarkers 대체)"""
        for marker in markers:
            center = marker['center']
            marker_id = marker['id']
            
            # 마커 중심에 원 그리기
            cv.circle(frame, center, 8, (0, 255, 255), -1)
            
            # ID 표시
            cv.putText(frame, f"ID:{marker_id}", (center[0] - 20, center[1] - 20),
                      cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # 거리 추정
            distance = 15000 / marker['area'] if marker['area'] > 0 else 0
            cv.putText(frame, f"{distance:.1f}cm", (center[0] - 30, center[1] + 30),
                      cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # 각 색상 영역 표시
            for region in marker['regions']:
                x, y, w, h = region['bbox']
                color_map = {'red': (0, 0, 255), 'green': (0, 255, 0), 'blue': (255, 0, 0)}
                color = color_map.get(region['color'], (255, 255, 255))
                cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        return frame

def start_detecting_simple_markers():
    """ArUco 대신 간단한 마커 탐지 시작"""
    print("=== 간단한 마커 탐지 시스템 ===")
    print("마커 종류:")
    print("ID 0: 빨간색")
    print("ID 1: 초록색") 
    print("ID 2: 파란색")
    print("ID 3: 빨간색 + 초록색")
    print("ID 4: 빨간색 + 파란색")
    print("ID 5: 초록색 + 파란색")
    print("ESC로 종료")
    
    detector = SimpleMarkerDetector()
    
    try:
        cap = cv.VideoCapture(0, cv.CAP_V4L2)
        if not cap.isOpened():
            print("카메라 열기 실패")
            return False
        
        print("카메라 열기 성공")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 마커 탐지
            markers = detector.detect_markers(frame)
            
            # 마커 표시
            frame = detector.draw_markers(frame, markers)
            
            # 상태 정보 표시
            cv.putText(frame, f"Markers: {len(markers)}", (10, 30),
                      cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # 탐지된 마커 정보 출력
            if markers:
                marker_info = ", ".join([f"ID{m['id']}" for m in markers])
                cv.putText(frame, marker_info, (10, 70),
                          cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            cv.imshow("Simple Marker Detection", frame)
            
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
        
        return True
        
    except Exception as e:
        print(f"마커 탐지 중 오류: {e}")
        return False
    finally:
        try:
            cap.release()
            cv.destroyAllWindows()
        except:
            pass

if __name__ == "__main__":
    start_detecting_simple_markers()
