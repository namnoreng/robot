import cv2
import numpy as np
import time

def detect_wheels_simple(frame):
    """OpenCV 기본 기능으로 바퀴(원형) 탐지"""
    
    # 그레이스케일 변환
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 가우시안 블러 적용
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # HoughCircles로 원형 탐지
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,  # 원 간 최소 거리
        param1=50,   # Canny edge detection의 상위 임계값
        param2=30,   # 원 검출 임계값 (낮을수록 더 많이 검출)
        minRadius=20, # 최소 반지름
        maxRadius=200 # 최대 반지름
    )
    
    detected_wheels = []
    
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for circle in circles[0, :]:
            x, y, radius = circle
            detected_wheels.append((x, y, radius))
            
            # 원과 중심점 그리기
            cv2.circle(frame, (x, y), radius, (0, 255, 0), 2)  # 원
            cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)       # 중심점
            
            # 정보 표시
            cv2.putText(frame, f"Wheel R:{radius}", (x-30, y-radius-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    return frame, detected_wheels

def detect_wheels_color_based(frame):
    """색상 기반 바퀴 탐지 (검은색/회색 바퀴 가정)"""
    
    # HSV 변환
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # 어두운 색상 범위 (바퀴 색상)
    lower_dark = np.array([0, 0, 0])
    upper_dark = np.array([180, 255, 80])
    
    # 마스크 생성
    mask = cv2.inRange(hsv, lower_dark, upper_dark)
    
    # 노이즈 제거
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # 윤곽선 찾기
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    detected_wheels = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if 500 < area < 10000:  # 면적 필터링
            # 외접 원 찾기
            (x, y), radius = cv2.minEnclosingCircle(contour)
            center = (int(x), int(y))
            radius = int(radius)
            
            # 원형도 체크 (면적 비율)
            circle_area = np.pi * radius * radius
            if area / circle_area > 0.6:  # 60% 이상 원형이면
                detected_wheels.append((center[0], center[1], radius))
                
                cv2.circle(frame, center, radius, (255, 0, 0), 2)
                cv2.circle(frame, center, 2, (255, 0, 0), 3)
                cv2.putText(frame, f"Color R:{radius}", (center[0]-30, center[1]-radius-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    return frame, detected_wheels

# 카메라 설정
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# FPS 계산용
fps_start_time = time.time()
fps_counter = 0

print("간단한 바퀴 탐지 (ESC로 종료)")
print("녹색: HoughCircles, 파란색: 색상 기반")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    start_time = time.time()
    
    # 두 가지 방법으로 바퀴 탐지
    frame, hough_wheels = detect_wheels_simple(frame.copy())
    frame, color_wheels = detect_wheels_color_based(frame)
    
    processing_time = time.time() - start_time
    
    # 성능 정보 표시
    fps_counter += 1
    if fps_counter % 30 == 0:
        fps_end_time = time.time()
        fps = 30 / (fps_end_time - fps_start_time)
        fps_start_time = fps_end_time
        print(f"FPS: {fps:.1f}, 처리시간: {processing_time*1000:.1f}ms")
    
    # 정보 표시
    cv2.putText(frame, f"Processing: {processing_time*1000:.1f}ms", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Hough: {len(hough_wheels)}, Color: {len(color_wheels)}", 
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow("Simple Wheel Detection", frame)
    
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("간단한 바퀴 탐지 종료")
