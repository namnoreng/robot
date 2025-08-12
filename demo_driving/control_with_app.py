# 기본적으로 필요한 모듈
import cv2 as cv
import numpy as np
import serial
import socket
import time
import platform
from cv2 import aruco

# 다른 모듈 불러오기
import driving
import detect_aruco

def configure_camera_manual_settings(cap, camera_name="Camera", exposure=-7, wb_temp=4000, brightness=128, contrast=128, saturation=128, gain=0):
    """
    카메라의 자동 기능을 비활성화하고 수동 설정을 적용하는 함수
    
    Parameters:
    - cap: cv2.VideoCapture 객체
    - camera_name: 카메라 이름 (로그용)
    - exposure: 노출 값 (-13 ~ -1, 낮을수록 어두움)
    - wb_temp: 화이트 밸런스 온도 (2800~6500K)
    - brightness: 밝기 (0~255)
    - contrast: 대비 (0~255)
    - saturation: 채도 (0~255)
    - gain: 게인 (0~255, 낮을수록 노이즈 적음)
    """
    print(f"=== {camera_name} 수동 설정 적용 ===")
    
    # 자동 기능 비활성화
    cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 자동 노출 비활성화 (수동 모드)
    cap.set(cv.CAP_PROP_AUTO_WB, 0)           # 자동 화이트 밸런스 비활성화
    
    # 수동 값 설정
    cap.set(cv.CAP_PROP_EXPOSURE, exposure)
    cap.set(cv.CAP_PROP_WB_TEMPERATURE, wb_temp)
    cap.set(cv.CAP_PROP_BRIGHTNESS, brightness)
    cap.set(cv.CAP_PROP_CONTRAST, contrast)
    cap.set(cv.CAP_PROP_SATURATION, saturation)
    cap.set(cv.CAP_PROP_GAIN, gain)
    
    # 설정 확인
    print(f"자동노출: {cap.get(cv.CAP_PROP_AUTO_EXPOSURE)} (0.25=수동)")
    print(f"노출값: {cap.get(cv.CAP_PROP_EXPOSURE)}")
    print(f"자동WB: {cap.get(cv.CAP_PROP_AUTO_WB)} (0=비활성화)")
    print(f"WB온도: {cap.get(cv.CAP_PROP_WB_TEMPERATURE)}K")
    print(f"밝기: {cap.get(cv.CAP_PROP_BRIGHTNESS)}")
    print(f"대비: {cap.get(cv.CAP_PROP_CONTRAST)}")
    print(f"채도: {cap.get(cv.CAP_PROP_SATURATION)}")
    print(f"게인: {cap.get(cv.CAP_PROP_GAIN)}")
    print("=" * (len(camera_name) + 16))

# 플랫폼 구분
current_platform = platform.system()

# 시리얼 통신 초기화 (윈도우/리눅스 분기)
if current_platform == "Windows":
    serial_port = "COM3"
elif current_platform == "Linux":
    serial_port = "/dev/ttyACM0"
else:
    serial_port = None

serial_server = None
if serial_port:
    try:
        serial_server = serial.Serial(serial_port, 115200)
        if serial_server.is_open:
            print(f"Serial communication is open. ({serial_port})")
            
            # 프로그램 시작 시 시리얼 버퍼 클리어 (이전 데이터 제거)
            serial_server.reset_input_buffer()
            serial_server.reset_output_buffer()
            print("Serial buffers cleared.")
            
            # 추가 안전장치: 버퍼에 남은 데이터 읽어서 버리기
            time.sleep(0.1)  # 짧은 대기
            while serial_server.in_waiting:
                old_data = serial_server.read().decode()
                print(f"Discarded old data: '{old_data}'")
            print("Serial initialization complete.")
        else:
            print("Failed to open serial communication.")
    except serial.SerialException as e:
        print(f"Serial communication error: {e}")
        serial_server = None

# 카메라 초기화 (윈도우/리눅스 분기) - 안정성 및 성능 강화
print("=== 카메라 초기화 시작 ===")

# 먼저 사용 가능한 카메라 인덱스 확인
available_cameras = []
for i in range(5):  # 0~4번 카메라 테스트
    test_cap = cv.VideoCapture(i)
    if test_cap.isOpened():
        available_cameras.append(i)
        test_cap.release()
    time.sleep(0.1)  # 짧은 대기

print(f"사용 가능한 카메라: {available_cameras}")

if len(available_cameras) == 0:
    print("❌ 사용 가능한 카메라가 없습니다.")
    exit(1)

# 카메라 초기화
if current_platform == "Windows":
    cap_front = cv.VideoCapture(0, cv.CAP_DSHOW) if 0 in available_cameras else None
    cap_back = cv.VideoCapture(1, cv.CAP_DSHOW) if 1 in available_cameras else None
else:
    # Jetson Nano에서 V4L2 백엔드 사용
    cap_front = cv.VideoCapture(0, cv.CAP_V4L2) if 0 in available_cameras else None
    cap_back = cv.VideoCapture(1, cv.CAP_V4L2) if 1 in available_cameras else None
    print("Jetson 환경 - V4L2 백엔드 사용")

if cap_front is None or not cap_front.isOpened():
    print("❌ 전방 카메라 초기 연결 실패")
    exit(1)

# 기본 해상도로 먼저 설정 (안정성 우선)
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 640)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
cap_front.set(cv.CAP_PROP_FPS, 30)

# 전방 카메라 안정화
print("전방 카메라 안정화 중...")
for i in range(10):
    ret, frame = cap_front.read()
    if ret:
        print(f"전방 프레임 {i+1}/10 읽기 성공")
    time.sleep(0.1)

# 이제 원하는 해상도로 설정
print("전방 카메라 목표 해상도 설정...")
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap_front.set(cv.CAP_PROP_FPS, 30)

# 전방 카메라 고급 설정
try:
    cap_front.set(cv.CAP_PROP_AUTOFOCUS, 0)  # 오토포커스 비활성화
    cap_front.set(cv.CAP_PROP_FOCUS, 0)      # 포커스 고정
    cap_front.set(cv.CAP_PROP_BUFFERSIZE, 1) # 최소 버퍼로 지연 최소화
    
    if current_platform == "Linux":  # Jetson 환경
        cap_front.set(cv.CAP_PROP_EXPOSURE, -6)   # 30fps에 맞춘 노출 시간
        print("Jetson용 30fps 최적화 설정 적용")
    else:
        # Windows 환경
        cap_front.set(cv.CAP_PROP_EXPOSURE, -6)   # 짧은 노출 시간
        cap_front.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # MJPEG 코덱 사용
        print("Windows용 카메라 설정 적용")
        
except Exception as e:
    print(f"전방 카메라 고급 설정 실패: {e}")

# 전방 카메라 수동 설정 적용 (플랫폼별 최적화)
try:
    if current_platform == "Linux":  # Jetson 환경
        configure_camera_manual_settings(cap_front, "전방 카메라", 
                                        exposure=-6, wb_temp=4000, brightness=128, 
                                        contrast=128, saturation=128, gain=15)
    else:
        # Windows 환경
        configure_camera_manual_settings(cap_front, "전방 카메라", 
                                        exposure=-6, wb_temp=4000, brightness=120, 
                                        contrast=130, saturation=128, gain=20)
except Exception as e:
    print(f"전방 카메라 수동 설정 실패: {e}")

# 후방 카메라 설정 (있는 경우)
if cap_back is not None and cap_back.isOpened():
    print("후방 카메라 설정 중...")
    
    # 기본 해상도로 먼저 설정
    cap_back.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    cap_back.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
    cap_back.set(cv.CAP_PROP_FPS, 30)
    
    # 후방 카메라 안정화
    for i in range(10):
        ret, frame = cap_back.read()
        if ret:
            print(f"후방 프레임 {i+1}/10 읽기 성공")
        time.sleep(0.1)
    
    # 목표 해상도 설정
    cap_back.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
    cap_back.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
    cap_back.set(cv.CAP_PROP_FPS, 30)
    
    # 후방 카메라 고급 설정
    try:
        cap_back.set(cv.CAP_PROP_AUTOFOCUS, 0)
        cap_back.set(cv.CAP_PROP_FOCUS, 0)
        cap_back.set(cv.CAP_PROP_BUFFERSIZE, 1)
        
        if current_platform == "Linux":
            cap_back.set(cv.CAP_PROP_EXPOSURE, -6)
        else:
            cap_back.set(cv.CAP_PROP_EXPOSURE, -6)
            cap_back.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
    except Exception as e:
        print(f"후방 카메라 고급 설정 실패: {e}")
    
    # 후방 카메라 수동 설정 적용
    try:
        if current_platform == "Linux":
            configure_camera_manual_settings(cap_back, "후방 카메라", 
                                            exposure=-6, wb_temp=4000, brightness=128, 
                                            contrast=128, saturation=128, gain=15)
        else:
            configure_camera_manual_settings(cap_back, "후방 카메라", 
                                            exposure=-6, wb_temp=4000, brightness=120, 
                                            contrast=130, saturation=128, gain=20)
    except Exception as e:
        print(f"후방 카메라 수동 설정 실패: {e}")
else:
    cap_back = None
    print("후방 카메라 사용 불가")

# 카메라 상태 최종 확인 및 테스트
print("=== 카메라 상태 최종 확인 ===")

# 전방 카메라 상태 확인
if cap_front.isOpened():
    print("✅ front camera is opened and configured")
    # 테스트 프레임 읽기
    ret, test_frame = cap_front.read()
    if ret and test_frame is not None and test_frame.size > 0:
        print(f"✅ 전방 카메라 테스트 프레임 읽기 성공 - 크기: {test_frame.shape}")
    else:
        print("❌ 전방 카메라 테스트 프레임 읽기 실패")
else:
    print("❌ front camera 열기 실패 - 프로그램 종료")
    exit(1)

# 후방 카메라 상태 확인
if cap_back is not None and cap_back.isOpened():
    print("✅ back camera is opened and configured")
    # 테스트 프레임 읽기
    ret, test_frame = cap_back.read()
    if ret and test_frame is not None and test_frame.size > 0:
        print(f"✅ 후방 카메라 테스트 프레임 읽기 성공 - 크기: {test_frame.shape}")
    else:
        print("❌ 후방 카메라 테스트 프레임 읽기 실패")
        cap_back.release()
        cap_back = None
        print("⚠️  후방 카메라 비활성화 - 전방 카메라만 사용")
else:
    print("⚠️  back camera 사용 불가 - front camera만 사용")
    cap_back = None

# npy 파일 불러오기
camera_front_matrix = np.load(r"camera_value/camera_front_matrix.npy")
dist_front_coeffs = np.load(r"camera_value/dist_front_coeffs.npy")

# 보정 행렬과 왜곡 계수를 불러옵니다.
print("Loaded front camera matrix : \n", camera_front_matrix)
print("Loaded front distortion coefficients : \n", dist_front_coeffs)

# back camera 파일이 있는 경우만 로드
camera_back_matrix = None
dist_back_coeffs = None
if cap_back is not None:
    try:
        camera_back_matrix = np.load(r"camera_value/camera_back_matrix.npy")
        dist_back_coeffs = np.load(r"camera_value/dist_back_coeffs.npy")
        print("Loaded back camera matrix : \n", camera_back_matrix)
        print("Loaded back distortion coefficients : \n", dist_back_coeffs)
    except FileNotFoundError:
        print("⚠️  back camera 보정 파일을 찾을 수 없습니다.")
        cap_back.release()
        cap_back = None

# OpenCV 버전 및 플랫폼에 따라 ArUco 파라미터 생성 방식 분기
cv_version = cv.__version__.split(".")
print(f"OpenCV 버전: {cv.__version__}, 플랫폼: {current_platform}")

# 플랫폼별 분기 처리 (Jetson의 경우 특별 처리)
if current_platform == "Linux":  # Jetson Nano/Xavier 등
    print("Jetson (Linux) 환경 - DetectorParameters_create() 사용")
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
    
    # Jetson용 파라미터 조정 (성능 최적화)
    param_markers.adaptiveThreshWinSizeMin = 3
    param_markers.adaptiveThreshWinSizeMax = 23
    param_markers.adaptiveThreshWinSizeStep = 10
    param_markers.adaptiveThreshConstant = 7
    param_markers.minMarkerPerimeterRate = 0.03
    param_markers.maxMarkerPerimeterRate = 4.0
    param_markers.polygonalApproxAccuracyRate = 0.03
    param_markers.minCornerDistanceRate = 0.05
    
elif int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
    print("OpenCV 3.2.x 이하 - 레거시 방식 사용")
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
else:
    print("OpenCV 4.x (Windows) - 신규 방식 사용")
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters()
    
    # Windows용 ArUco 검출 파라미터 조정 (검출 성능 향상)
    param_markers.adaptiveThreshWinSizeMin = 3
    param_markers.adaptiveThreshWinSizeMax = 23
    param_markers.adaptiveThreshWinSizeStep = 10
    param_markers.adaptiveThreshConstant = 7
    param_markers.minMarkerPerimeterRate = 0.03
    param_markers.maxMarkerPerimeterRate = 4.0
    param_markers.polygonalApproxAccuracyRate = 0.03
    param_markers.minCornerDistanceRate = 0.05

print("=== 카메라 및 ArUco 초기화 완료 ===")

# 클라이언트 소켓 초기화 (서버에 접속)
host_input = input("Enter server IP (default: 127.0.0.1): ").strip()
port_input = input("Enter server port (default: 12345): ").strip()
HOST = host_input if host_input else '127.0.0.1'
PORT = int(port_input) if port_input else 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print(f"[Client] Connected to server: {HOST}:{PORT}")

# 서버에 기기 타입 전송 (예: robot)
client_socket.sendall(b"robot\n")

try:
    while True:
        # 서버로부터 명령을 받음
        data = client_socket.recv(1024)
        if not data:
            print("[Client] Server disconnected")
            break
        command = data.decode().strip()
        print(f"[Server] Command received: {command}")

        # 명령에 따라 동작 수행 (아래는 예시)
        if command.startswith("PARK"):
            # 예: "PARK,1,left,2,right,1234"
            try:
                _, sector, side, subzone, direction, car_number = command.split(",")
                sector = int(sector)
                subzone = int(subzone)
                # 목적지 정보(sector, side, subzone, direction)를 활용해서 직접 주행 로직 작성
                # 예시: auto driving 모드처럼 직접 명령 조합
                print(f"[Client] 목적지: {sector}, {side}, {subzone}, {direction}, {car_number}")

                # 입차 시작: 차량 들어올리기 동작
                print("[Client] 차량 들어올리기 시작...")
                if serial_server is not None:
                    # 7번 명령 전 버퍼 클리어 (안전장치)
                    serial_server.reset_input_buffer()
                    
                    serial_server.write(b"7")  # 차량 들어올리기 명령
                    print("[Client] 들어올리기 완료 신호('a') 대기 중...")
                    
                    # STM32로부터 'a' 신호 대기
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 시리얼 수신: '{recv}'")
                            if recv == "a":
                                print("[Client] 차량 들어올리기 완료!")
                                break
                            else:
                                print(f"[Client] 예상치 못한 신호: '{recv}' - 계속 대기...")
                        time.sleep(0.1)
                    
                    # 들어올리기 완료 후 정지 및 안정화
                    serial_server.write(b"9")  # 정지 명령
                    time.sleep(2)  # 2초 안정화 대기
                    
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    serial_server.reset_output_buffer()
                    
                    print("[Client] 시스템 안정화 완료, 주행 시작")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                    time.sleep(2)  # 시리얼이 없으면 2초 대기

                # 예시: 첫 번째 마커까지 직진
                print("[Client] 첫 번째 마커로 직진 시작")
                if serial_server is not None:
                    serial_server.write(b"1")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=sector, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, target_distance=0.35)
                
                # 마커 인식 후 정지
                client_socket.sendall(f"sector_arrived,{sector},None,None\n".encode())
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(0.5)

                # 방향에 따라 회전
                if side == "left":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"3")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                elif side == "right":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"4")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                print("sector 회전 완료 ")
                driving.flush_camera(cap_front, 5)  # 카메라 플러시
                time.sleep(1)
                if serial_server is not None:
                    serial_server.write(b"9")

                if serial_server is not None:
                    serial_server.write(b"1")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=subzone, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, target_distance=0.38)
                if serial_server is not None:
                    serial_server.write(b"9")

                # subzone 도착 후 서버에 신호 전송
                print("[Client] subzone 도착 신호 전송")
                client_socket.sendall(f"subzone_arrived,{sector},{side},{subzone}\n".encode())
                time.sleep(0.5)

                # subzone 도착 후 로봇 초기화
                # driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=subzone, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)

                # 방향에 따라 회전
                if direction == "left":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"4")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                elif direction == "right":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"3")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                print("subzone 회전 완료")
                driving.flush_camera(cap_front, 5)  # 카메라 플러시
                time.sleep(1)
                if serial_server is not None:
                    serial_server.write(b"9")

                # 복합 후진 제어 함수 호출 (명시적으로 마커 1, 2 사용) - 주석처리
                # success = driving.advanced_parking_control(
                #     cap_front, cap_back, marker_dict, param_markers,
                #     camera_front_matrix, dist_front_coeffs,
                #     camera_back_matrix, dist_back_coeffs, serial_server,
                #     back_marker_id=1, front_marker_id=2
                # )
                
                # if success:
                #     print("[Client] 복합 후진 제어 성공")
                # else:
                #     print("[Client] 복합 후진 제어 실패 - 기본 후진으로 대체")
                #     # 실패 시 기본 후진
                #     if serial_server is not None:
                #         serial_server.write(b"2")
                #         time.sleep(2)  # 2초간 후진
                #         serial_server.write(b"9")
                
                # 간단한 후진 제어: 마커 1번 인식까지 후진
                print("[Client] 마커 1번 인식까지 후진 시작...")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                
                # 뒷카메라로 마커 1번 인식
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=1, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                    print("[Client] 뒷카메라로 마커 1번 인식 완료")
                else:
                    # 뒷카메라가 없으면 전방카메라로 대체
                    print("[Client] 뒷카메라가 없어 전방카메라로 대체")
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=1, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                    print("[Client] 전방카메라로 마커 1번 인식 완료")
                
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                print("[Client] 마커 1번까지 후진 완료")
                
                time.sleep(1)  # 안정화 대기
                
                # 주차공간 도착 후 차량 내려놓기
                print("[Client] 차량 내려놓기 시작...")
                if serial_server is not None:
                    # 8번 명령 전 버퍼 클리어 (안전장치)
                    serial_server.reset_input_buffer()
                    
                    serial_server.write(b"8")  # 차량 내려놓기 명령
                    print("[Client] 내려놓기 완료 신호('c') 대기 중...")
                    
                    # STM32로부터 'c' 신호 대기
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 시리얼 수신: '{recv}'")
                            if recv == "c":
                                print("[Client] 차량 내려놓기 완료!")
                                break
                            else:
                                print(f"[Client] 예상치 못한 신호: '{recv}' - 계속 대기...")
                        time.sleep(0.1)
                    
                    # 내려놓기 완료 후 정지 및 안정화
                    serial_server.write(b"9")  # 정지 명령
                    time.sleep(1)  # 1초 안정화 대기
                    
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    serial_server.reset_output_buffer()
                    
                    print("[Client] 차량 내려놓기 시스템 안정화 완료")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                    time.sleep(3)  # 시리얼이 없으면 3초 대기
                
                # 주차 완료 신호를 서버에 전송
                print(f"[Client] 주차 완료: {sector},{side},{subzone},{direction},{car_number}")
                client_socket.sendall(f"DONE,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                
                # 주차 완료 후 제자리로 복귀
                print("[Client] 제자리 복귀 시작...")
                
                # 1. 주차 공간에서 나오기 (마커 2번 인식 후 추가 직진하여 두 번째 0번에서 멈춤)
                print("[Client] 주차 공간에서 탈출 중... (마커 2번 인식 후 추가 직진)")
                if serial_server is not None:
                    serial_server.write(b"1")  # 전진 시작
                
                # 먼저 마커 2번을 인식할 때까지 전진
                driving.flush_camera(cap_back, 5) if cap_back is not None else None
                driving.flush_camera(cap_front, 5)
                print("[Client] 마커 2번 인식 중...")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=2, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, target_distance=0.42)
                
                # 마커 2번 인식 후 추가로 직진하여 두 번째 0번 마커 근처로 이동
                print("[Client] 마커 2번 인식 완료, 추가 직진하여 두 번째 0번 마커로...")
                
                # 이제 0번 마커 인식 (두 번째 0번이어야 함)
                print("[Client] 두 번째 0번 마커 인식 시작...")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=0, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, target_distance=0.40)
                
                # 탈출 성공
                client_socket.sendall(f"subzone_arrived,{sector},{side},{subzone}\n".encode())

                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                    time.sleep(0.5)
                
                # 2. 돌아갈 방향으로 회전 (주차할 때와 반대)
                print("[Client] 복귀를 위한 회전...")
                if serial_server is not None:
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    if direction == "left":
                        serial_server.write(b"3")  # 원래 왔던 방향과 반대로
                    elif direction == "right":
                        serial_server.write(b"4")
                    
                    # 회전 완료 신호 대기
                    timeout_count = 0
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 회전 신호 수신: '{recv}'")
                            if recv == "s":
                                break
                        time.sleep(0.1)
                        timeout_count += 1
                        if timeout_count > 100:  # 10초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                driving.flush_camera(cap_back, 5)  # 카메라 플러시
                driving.flush_camera(cap_front, 5)  # 카메라 플러시

                # 3. 두 번째 마커로 복귀 (후진하면서 뒷카메라로 인식)
                print("[Client] 두 번째 마커로 복귀 중... (후진, 뒷카메라 사용, 마커 0번 인식)")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                # 뒷카메라로 마커 0번 인식
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=0, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs, target_distance=0.45)
                else:
                    print("[Client] 뒷카메라가 없어 전방카메라로 대체")
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=0, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, target_distance=0.45)               
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                    client_socket.sendall(f"sector_arrived,{sector},None,None\n".encode()) # sector 도착
                    time.sleep(0.5)
                
                # 4. 첫 번째 회전 방향과 반대로 회전
                print("[Client] 첫 번째 마커 방향으로 회전...")
                if serial_server is not None:
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    if side == "left":
                        serial_server.write(b"4")  # 왔던 방향과 반대
                    elif side == "right":
                        serial_server.write(b"3")
                    
                    # 회전 완료 신호 대기
                    timeout_count = 0
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 회전 신호 수신: '{recv}'")
                            if recv == "s":
                                break
                        time.sleep(0.1)
                        timeout_count += 1
                        if timeout_count > 100:  # 10초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                # 5. 초기 위치로 복귀 (첫 번째 마커까지 후진하면서 뒷카메라로)
                print("[Client] 초기 위치로 복귀 중... (후진, 뒷카메라 사용, 마커 3번 인식)")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                # 뒷카메라로 마커 3번 인식
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=3, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                else:
                    print("[Client] 뒷카메라가 없어 전방카메라로 대체")
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=3, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    client_socket.sendall(f"starting_point,0,None,None\n".encode())
                    serial_server.write(b"9")  # 정지
                
                # 6. 최종 위치 조정 (마커 17로 이동 - 초기 대기 위치)
                print("[Client] 최종 대기 위치로 이동...")
                #if serial_server is not None:
                    # driving.initialize_robot(cap_back, marker_dict, param_markers, 3, serial_server, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs, is_back_camera=True)

                print("[Client] 제자리 복귀 완료!")
                
                # 대기 위치 복귀 완료 신호를 서버에 전송
                client_socket.sendall(f"COMPLETE\n".encode())

                # 필요하다면 추가 주행/회전/정지 등 구현

                client_socket.sendall(b"OK: PARK command received\n")
            except Exception as e:
                print(f"[Client] PARK 명령 파싱 오류: {e}")
                client_socket.sendall(b"ERROR: PARK command parse error\n")
        elif command.startswith("OUT"):
            # 예: "OUT,sector,side,subzone,direction,car_number" (서버에서 위치 정보 포함하여 전송)
            try:
                parts = command.split(",")
                if len(parts) == 6:
                    # 서버에서 위치 정보를 포함하여 전송한 경우
                    _, sector, side, subzone, direction, car_number = parts
                    sector = int(sector)
                    subzone = int(subzone)
                    print(f"[Client] 출차 요청 - 차량번호: {car_number}, 위치: {sector},{side},{subzone},{direction}")
                elif len(parts) == 2:
                    # 기존 방식: 차량번호만 전송된 경우 (하위 호환성)
                    _, car_number = parts
                    print(f"[Client] 출차 요청 차량번호: {car_number}")
                    
                    # 차량 위치 조회 (parking_status.json에서 검색)
                    import json
                    try:
                        with open("parking_status.json", "r", encoding="utf-8") as f:
                            parking_data = json.load(f)
                        
                        # 차량번호로 위치 찾기
                        car_location = None
                        for sector_key, sector_data in parking_data.items():
                            if sector_key == "total_spaces":
                                continue
                            for side_key, side_data in sector_data.items():
                                for subzone_key, subzone_data in side_data.items():
                                    for direction_key, direction_data in subzone_data.items():
                                        if direction_data.get("car_number") == car_number:
                                            car_location = {
                                                "sector": int(sector_key.replace("sector_", "")),
                                                "side": side_key,
                                                "subzone": int(subzone_key.replace("subzone_", "")),
                                                "direction": direction_key
                                            }
                                            break
                                    if car_location:
                                        break
                                if car_location:
                                    break
                            if car_location:
                                break
                        
                        if not car_location:
                            print(f"[Client] 차량번호 {car_number}를 찾을 수 없습니다.")
                            client_socket.sendall(f"ERROR: Car {car_number} not found\n".encode())
                            continue
                        
                        print(f"[Client] 차량 위치 발견: {car_location}")
                        sector = car_location["sector"]
                        side = car_location["side"]
                        subzone = car_location["subzone"]
                        direction = car_location["direction"]
                        
                    except FileNotFoundError:
                        print("[Client] parking_status.json 파일을 찾을 수 없습니다.")
                        client_socket.sendall(b"ERROR: Parking status file not found\n")
                        continue
                    except json.JSONDecodeError:
                        print("[Client] parking_status.json 파일 파싱 오류")
                        client_socket.sendall(b"ERROR: Parking status file parse error\n")
                        continue
                else:
                    print(f"[Client] OUT 명령 형식 오류: {command}")
                    client_socket.sendall(b"ERROR: Invalid OUT command format\n")
                    continue
                
                # 2. 차량 위치로 이동 (입차와 동일한 경로)
                print(f"[Client] 차량 위치로 이동 시작: {sector}, {side}, {subzone}, {direction}")
                
                # 첫 번째 마커까지 직진
                print("[Client] 첫 번째 마커로 직진 시작")
                if serial_server is not None:
                    serial_server.write(b"1")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=sector, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(0.5)

                # 방향에 따라 회전
                if side == "left":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"3")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                elif side == "right":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"4")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                print("sector 회전 완료")
                driving.flush_camera(cap_front, 5)
                time.sleep(0.5)
                if serial_server is not None:
                    serial_server.write(b"9")

                # 두 번째 마커까지 직진
                if serial_server is not None:
                    serial_server.write(b"1")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=subzone, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(0.5)

                # 방향에 따라 회전
                if direction == "left":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"4")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                elif direction == "right":
                    if serial_server is not None:
                        # 시리얼 버퍼 클리어
                        serial_server.reset_input_buffer()
                        serial_server.write(b"3")
                        timeout_count = 0
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 회전 신호 수신: '{recv}'")
                                if recv == "s":
                                    break
                            time.sleep(0.1)
                            timeout_count += 1
                            if timeout_count > 100:  # 10초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                print("subzone 회전 완료")
                driving.flush_camera(cap_front, 5)
                time.sleep(0.5)
                if serial_server is not None:
                    serial_server.write(b"9")

                # 3. 차량 들어올리기 (7번 명령으로 진입)
                print("[Client] 차량 들어올리기 시작...")
                if serial_server is not None:
                    serial_server.write(b"7")  # 차량 들어올리기 명령
                    print("[Client] 들어올리기 완료 신호('a') 대기 중...")
                    
                    # STM32로부터 'a' 신호 대기
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            if recv == "a":
                                print("[Client] 차량 들어올리기 완료!")
                                break
                    
                    # 들어올리기 완료 후 정지 및 안정화
                    serial_server.write(b"9")
                    time.sleep(3)
                    
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    serial_server.reset_output_buffer()
                    
                    print("[Client] 시스템 안정화 완료, 복귀 시작")

                # 4. 마커 17(차량 대기 위치)로 복귀 (입차와 동일한 복귀 로직)
                print("[Client] 차량 대기 위치로 복귀 시작...")
                
                # 주차 공간에서 나오기 (마커 0번과의 거리가 0.3m 이상이 될 때까지)
                print("[Client] 주차 공간에서 탈출 중... (마커 0번과의 거리가 0.3m 이상이 될 때까지)")
                if serial_server is not None:
                    serial_server.write(b"1")
                escape_success = driving.escape_from_parking(cap_front, marker_dict, param_markers, marker_index=0, 
                                                   camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, 
                                                   target_distance=0.3)
                if serial_server is not None:
                    serial_server.write(b"9")
                    time.sleep(0.5)
                
                # 돌아갈 방향으로 회전
                print("[Client] 복귀를 위한 회전...")
                if serial_server is not None:
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    if direction == "left":
                        serial_server.write(b"3")
                    elif direction == "right":
                        serial_server.write(b"4")
                    
                    timeout_count = 0
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 회전 신호 수신: '{recv}'")
                            if recv == "s":
                                break
                        time.sleep(0.1)
                        timeout_count += 1
                        if timeout_count > 100:  # 10초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                # 두 번째 마커로 복귀 (후진, 뒷카메라)
                print("[Client] 두 번째 마커로 복귀 중... (후진, 뒷카메라 사용, 마커 0번 인식)")
                if serial_server is not None:
                    serial_server.write(b"2")
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=0, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                else:
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=0, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                    time.sleep(0.5)
                
                # 첫 번째 회전 방향과 반대로 회전
                print("[Client] 첫 번째 마커 방향으로 회전...")
                if serial_server is not None:
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    if side == "left":
                        serial_server.write(b"4")
                    elif side == "right":
                        serial_server.write(b"3")
                    
                    timeout_count = 0
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 회전 신호 수신: '{recv}'")
                            if recv == "s":
                                break
                        time.sleep(0.1)
                        timeout_count += 1
                        if timeout_count > 100:  # 10초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                # 첫 번째 마커로 복귀 (후진, 뒷카메라)
                print("[Client] 첫 번째 마커로 복귀 중... (후진, 뒷카메라 사용, 마커 3번 인식)")
                if serial_server is not None:
                    serial_server.write(b"2")
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=3, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                else:
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=3, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                
                # 5. 차량 대기 장소로 이동 (기존 복합 후진 제어 함수 활용) - 주석처리
                # print("[Client] 차량 대기 장소로 이동... (복합 후진 제어)")
                
                # 기존 advanced_parking_control 함수 사용 (마커 17, 3 사용) - 주석처리
                # success = driving.advanced_parking_control(
                #     cap_front, cap_back, marker_dict, param_markers,
                #     camera_front_matrix, dist_front_coeffs,
                #     camera_back_matrix, dist_back_coeffs, serial_server,
                #     back_marker_id=17, front_marker_id=3
                # )
                
                # if success:
                #     print("[Client] 차량 대기 장소 도착 성공")
                # else:
                #     print("[Client] 복합 후진 제어 실패 - 기본 후진으로 대체")
                #     # 실패 시 기본 후진으로 마커 17까지 이동
                #     if serial_server is not None:
                #         serial_server.write(b"2")  # 후진
                #     driving.driving(cap_back if cap_back is not None else cap_front, marker_dict, param_markers, marker_index=17, 
                #                   camera_matrix=camera_back_matrix if cap_back is not None else camera_front_matrix, 
                #                   dist_coeffs=dist_back_coeffs if cap_back is not None else dist_front_coeffs)
                #     if serial_server is not None:
                #         serial_server.write(b"9")  # 정지
                
                # 간단한 후진 제어: 마커 17번 인식까지 후진
                print("[Client] 마커 17번 인식까지 후진 시작...")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                
                # 뒷카메라로 마커 17번 인식
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=17, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                    print("[Client] 뒷카메라로 마커 17번 인식 완료")
                else:
                    # 뒷카메라가 없으면 전방카메라로 대체
                    print("[Client] 뒷카메라가 없어 전방카메라로 대체")
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=17, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                    print("[Client] 전방카메라로 마커 17번 인식 완료")
                
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                print("[Client] 마커 17번까지 후진 완료")
                
                # 6. 차량 내려놓기
                print("[Client] 차량 내려놓기 시작...")
                if serial_server is not None:
                    # 8번 명령 전 버퍼 클리어 (안전장치)
                    serial_server.reset_input_buffer()
                    
                    serial_server.write(b"8")  # 차량 내려놓기 명령
                    print("[Client] 내려놓기 완료 신호('c') 대기 중...")
                    
                    # STM32로부터 'c' 신호 대기
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 시리얼 수신: '{recv}'")
                            if recv == "c":
                                print("[Client] 차량 내려놓기 완료!")
                                break
                            else:
                                print(f"[Client] 예상치 못한 신호: '{recv}' - 계속 대기...")
                        time.sleep(0.1)
                    
                    # 내려놓기 완료 후 정지 및 안정화
                    serial_server.write(b"9")  # 정지 명령
                    time.sleep(1)  # 1초 안정화 대기
                    
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    serial_server.reset_output_buffer()
                    
                    print("[Client] 차량 내려놓기 시스템 안정화 완료")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                    time.sleep(3)  # 시리얼이 없으면 3초 대기
                
                # 출차 완료 신호를 서버에 전송
                print(f"[Client] 출차 완료 신호 전송: {sector},{side},{subzone},{direction},{car_number}")
                client_socket.sendall(f"OUT_DONE,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                
                # 7. 로봇 초기 위치로 복귀 (전진)
                print("[Client] 로봇 초기 위치로 복귀... (전진)")
                if serial_server is not None:
                    serial_server.write(b"1")  # 전진
                # 로봇 초기 위치까지 전진 (마커 17 인식)
                driving.driving(cap_front, marker_dict, param_markers, marker_index=17, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                
                # 8. 로봇 초기 위치 정밀 정렬 (마커 17 기준으로 중앙+수직 정렬)
                print("[Client] 로봇 초기 위치 정밀 정렬...")
                if serial_server is not None:
                    driving.initialize_robot(cap_front, marker_dict, param_markers, 17, serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, is_back_camera=False)
                
                print(f"[Client] 출차 완료: {car_number}")
                
                # 대기 위치 복귀 완료 신호를 서버에 전송
                client_socket.sendall(f"COMPLETE\n".encode())
                
                client_socket.sendall(f"OK: OUT {car_number} completed\n".encode())
                
            except Exception as e:
                print(f"[Client] OUT 명령 처리 오류: {e}")
                client_socket.sendall(b"ERROR: OUT command process error\n")
        elif command == "detect_aruco":
            detect_aruco.start_detecting_aruco(cap_front, marker_dict, param_markers)
            client_socket.sendall(b"OK: detect_aruco\n")
        elif command == "driving":
            driving.driving(cap_front, marker_dict, param_markers, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
            client_socket.sendall(b"OK: driving\n")
        elif command == "auto_driving":
            client_socket.sendall(b"OK: auto_driving\n")
        elif command == "reset_position":
            if serial_server is not None:
                driving.initialize_robot(cap_front, marker_dict, param_markers, 17, serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, is_back_camera=False)
            else:
                print("[Client] 시리얼 통신이 연결되지 않아 초기화를 수행할 수 없습니다.")
            client_socket.sendall(b"OK: reset_position\n")
        elif command == "stop":
            client_socket.sendall(b"OK: stop\n")
            break
        elif command == "camera_test":
            print("[Client] 카메라 테스트 시작")
            # 앞/뒤 카메라 각각 테스트
            print("[Client] front camera test")
            detect_aruco.start_detecting_aruco(cap_front, marker_dict, param_markers)
            if cap_back is not None:
                print("[Client] back camera test")
                detect_aruco.start_detecting_aruco(cap_back, marker_dict, param_markers)
            else:
                print("[Client] back camera는 사용할 수 없습니다.")
            client_socket.sendall(b"OK: camera_test\n")
        else:
            client_socket.sendall(b"Unknown command\n")
            print("[Client] Unknown command sent. Closing connection.")
        
except Exception as e:
    print(f"[Client] Error: {e}")

# 안전한 프로그램 종료
print("=== 프로그램 정리 중 ===")
try:
    client_socket.close()
    print("소켓 연결 종료 완료")
except:
    pass

try:
    if cap_front is not None:
        cap_front.release()
        print("전방 카메라 해제 완료")
except:
    pass

try:
    if cap_back is not None:
        cap_back.release()
        print("후방 카메라 해제 완료")
except:
    pass

try:
    cv.destroyAllWindows()
    print("OpenCV 윈도우 정리 완료")
except:
    pass

print("프로그램 종료 완료")
