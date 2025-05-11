import cv2
import numpy as np
from pymycobot.myagv import MyAgv
import threading
import time

# AGV의 동작 상태를 저장하는 변수 (중복 실행 방지)
state = threading.Lock()

# MyAgv 객체 생성 (시리얼 포트와 보드레이트 설정)
agv =  ("/dev/ttyAMA2", 115200)

# PID 제어를 위한 변수 설정
Kp = 0.5
Ki = 0.1
Kd = 0.05
integral = 0
previous_error = 0
initial_speed = 10  # 초기 속도 설정
max_speed = 50  # 최대 속도 설정
speed_increment = 2  # 속도 증가량

# PID 제어 함수
def pid_control(error, dt):
    global integral, previous_error
    integral += error * dt
    derivative = (error - previous_error) / dt
    output = Kp * error + Ki * integral + Kd * derivative
    previous_error = error
    return output

# 카메라에서 받아온 프레임을 처리하는 함수
def process_frame(frame):
    # 프레임의 높이와 너비를 구함
    height, width, _ = frame.shape
    
    # 관심 영역(ROI)의 높이 설정 (아래쪽 1/2 영역)
    roi_height = int(height / 2)
    roi_top = height - roi_height
    roi = frame[roi_top:, :]  # ROI 설정
    
    # 화면에 중앙선(흰색) 그리기
    center_line = width // 2
    cv2.line(roi, (center_line, 0), (center_line, roi_height), (255, 255, 255), 2)
    
    # ROI 영역을 HSV 색상 공간으로 변환
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # 특정 색상 범위를 설정 (예: 빨간색)
    lower_color = np.array([0, 50, 50], dtype=np.uint8)
    upper_color = np.array([10, 255, 255], dtype=np.uint8)
    
    # 색상에 해당하는 마스크 생성
    color_mask = cv2.inRange(hsv, lower_color, upper_color)
    
    # 블러 처리 추가하여 노이즈 제거
    blurred = cv2.GaussianBlur(color_mask, (5, 5), 0)
    
    # 윤곽선을 찾기 위해 Contour 검출
    contours, _ = cv2.findContours(blurred, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        [vx, vy, x, y] = cv2.fitLine(largest_contour, cv2.DIST_L2, 0, 0.01, 0.01)
        
        # 각도 계산 (기울기 기반)
        angle = np.arctan2(vy, vx) * 180 / np.pi
        
        # 윤곽선의 중심 좌표 계산
        M = cv2.moments(largest_contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
        else:
            cx = width // 2
        
        offset = cx - center_line  # 중심에서 벗어난 거리
        return offset, angle
    return None, None

# AGV 명령 실행 함수 (급커브와 약한 커브 대응)
def execute_command(offset, angle, MA, frame, cap):
    global initial_speed, max_speed
    global initial_speed
    with state:
        if offset is None:
            print("라인을 찾을 수 없음, 라인 재탐색 중")
            MA.counterclockwise_rotation(50, 0.3)
            time.sleep(0.5)
            ret, frame = cap.read()
            if not ret:
                print("Camera error")
                return
            offset, angle = process_frame(frame)
            if offset is None:
                return
        
        # 중앙선 기준으로 방향 조절
        dt = 0.1  # PID 제어에서 사용할 시간 간격
        error = offset
        control_signal = pid_control(error, dt)
        
        # 약한 커브와 급커브에 대한 속도 및 회전 반응 차별화
        # 각도에 따라 회전 속도 및 방향 조절
        angle_abs = abs(angle)
        if angle_abs < 10:  # 각도가 작으면 약한 커브
            print("약한 커브, 부드럽게 회전 중")
            if initial_speed < max_speed:
                initial_speed += speed_increment  # 점진적으로 속도 증가
            speed = initial_speed
            rotation_speed = 30 + int(angle_abs * 2)  # 각도에 비례하여 회전 속도 설정
            if control_signal < 0:
                MA.counterclockwise_rotation(rotation_speed, 0.3)
            else:
                MA.clockwise_rotation(rotation_speed, 0.3)
            time.sleep(0.1)
        else:  # 급커브
            print("급커브, 속도 조절 중")
            speed = 20  # 급커브일 때 속도를 낮춤
            rotation_speed = 50 + int(angle_abs * 1.5)  # 각도에 비례하여 회전 속도 설정
            if control_signal < 0:
                print("왼쪽으로 급커브 회전 중")
                MA.counterclockwise_rotation(rotation_speed, 0.4)
            else:
                print("오른쪽으로 급커브 회전 중")
                MA.clockwise_rotation(rotation_speed, 0.4)
            time.sleep(0.5)
        
        # 직진 명령
        print("직진 중")
        MA.go_ahead(speed, 0.3)  # 직진 시에는 속도 증가

# 카메라 스레드 함수
def camera_thread():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera error")
            break
        
        offset, angle = process_frame(frame)
        global last_offset, last_angle
        if offset is not None and angle is not None:
            last_offset, last_angle = offset, angle
        
        if offset is not None:
            print(f"Offset: {offset}, Angle: {angle}")
            execute_command(offset, angle, agv, frame, cap)
        
        cv2.imshow("Frame", frame)
        if cv2.waitKey(150) & 0xFF == ord('q'):
            stop(agv)
            break
    
    cap.release()
    cv2.destroyAllWindows()

# AGV 정지 함수
def stop(MA):
    with state:
        MA.stop()
    print("stop")

# 카메라 스레드 실행
camera_thread = threading.Thread(target=camera_thread)
camera_thread.start()
camera_thread.join()

