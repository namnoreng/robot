#!/usr/bin/env python3
"""
CSI 카메라 전용 버전 - 로봇 제어 앱
Jetson Nano CSI 카메라 전용 (USB 카메라 미지원)
GStreamer 파이프라인을 통한 CSI 카메라 최적화
"""

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

# 코드 내에서 사용할 상수 및 변수 정의
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

# 기본 ArUco 인식 거리 설정 (미터 단위)
DEFAULT_ARUCO_DISTANCE = 0.145
MARKER2_ARUCO_DISTANCE = 0.03
MARKER0_ARUCO_DISTANCE = 0.038

def gstreamer_pipeline(capture_width=640, capture_height=480, 
                      display_width=640, display_height=480, 
                      framerate=30, flip_method=0, sensor_id=0):
    """CSI 카메라용 GStreamer 파이프라인 최적화"""
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        "video/x-raw(memory:NVMM), "
        f"width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width={display_width}, height={display_height}, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink drop=true max-buffers=2"
    )

def configure_csi_camera_settings(cap, camera_name="CSI Camera"):
    """
    CSI 카메라용 간단한 설정 함수
    CSI 카메라는 GStreamer 파이프라인에서 대부분 설정되므로 최소한만 설정
    """
    print(f"=== {camera_name} CSI 설정 확인 ===")
    
    try:
        # 버퍼 설정만 적용 (나머지는 GStreamer에서 처리)
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)  # 최소 버퍼로 지연 최소화
        print("✅ CSI 카메라 버퍼 설정 완료")
        
        # 현재 설정 확인만 수행 (설정 변경 시도하지 않음)
        width = cap.get(cv.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        fps = cap.get(cv.CAP_PROP_FPS)
        
        print(f"현재 해상도: {width}x{height}")
        print(f"현재 FPS: {fps}")
        print("✅ CSI 카메라는 GStreamer 파이프라인 설정 사용")
        
    except Exception as e:
        print(f"⚠️ {camera_name} 설정 확인 중 오류: {e}")
    
    print("=" * (len(camera_name) + 20))

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

def receive_vehicle_distance_data():
    """
    차량 리프팅 후 STM32에서 전송하는 차량과 로봇 간격 데이터를 수신
    예상 데이터 형식: "150" (mm 단위 정수값, 예: 150mm)
    """
    if not serial_server or not serial_server.is_open:
        print("시리얼 연결이 없어 간격 데이터를 받을 수 없습니다.")
        return None
    
    try:
        # STM32에서 간격 데이터가 올 때까지 대기 (타임아웃 5초)
        timeout_start = time.time()
        buffer = ""
        
        while time.time() - timeout_start < 5.0:  # 5초 타임아웃
            if serial_server.in_waiting > 0:
                char = serial_server.read().decode()
                buffer += char
                
                # 줄바꿈 문자가 오면 완성된 메시지로 처리
                if char == '\n' or char == '\r':
                    message = buffer.strip()
                    if message.isdigit():  # 숫자인지 확인
                        try:
                            distance_mm = int(message)  # mm 단위 정수로 변환
                            distance_cm = distance_mm / 10.0  # cm 단위로 변환하여 표시
                            print(f"차량 간격 데이터 수신: {distance_mm}mm ({distance_cm}cm)")
                            return distance_mm
                        except ValueError as e:
                            print(f"간격 데이터 변환 오류: {e}")
                    elif message:  # 빈 문자열이 아닌 경우만 오류 표시
                        print(f"간격 데이터 형식 오류: '{message}' (숫자가 아님)")
                    buffer = ""  # 버퍼 초기화
            
            time.sleep(0.01)  # CPU 부하 감소
        
        print("차량 간격 데이터 수신 타임아웃 (5초)")
        return None
        
    except Exception as e:
        print(f"간격 데이터 수신 오류: {e}")
        return None

def calculate_aruco_target_distance(measured_gap_mm):
    """
    측정된 거리를 바탕으로 ArUco 마커 인식 목표 거리를 계산 (단순 빼기)
    
    Parameters:
    - measured_gap_mm: 측정된 거리 (mm) - 센서에서 차량까지의 거리
    
    Returns:
    - target_distance: ArUco 마커 인식용 목표 거리 (m 단위)
    
    계산 공식:
    - 목표거리 = 측정거리 - 고정오프셋(80mm)
    """
    
    if measured_gap_mm is None:
        # 간격 데이터가 없으면 기본값 사용
        print("[거리 계산] 간격 데이터 없음, 기본 거리 사용")
        return DEFAULT_ARUCO_DISTANCE
    
    # 고정 오프셋 (일단은 0으로 설정, 필요시 조정)
    OFFSET_MM = 0
    
    # 단순 빼기로 목표 거리 계산
    target_distance_mm = 150 - (measured_gap_mm - OFFSET_MM)

    # 최소값 보정 (13cm = 130mm 이하로는 안됨)
    if target_distance_mm < 130:
        print(f"[거리 계산] 계산된 거리({target_distance_mm}mm)가 너무 작음 - 최소 거리 사용")
        target_distance_mm = 130  # 최소 13cm

    # mm를 m로 변환
    target_distance_m = target_distance_mm / 1000.0

    # 안전 범위 제한 (0.1m ~ 0.2m)
    target_distance_m = max(0.1, min(0.2, target_distance_m))

    print(f"[거리 계산] 측정 거리: {measured_gap_mm}mm")
    print(f"[거리 계산] 오프셋: {OFFSET_MM}mm")
    print(f"[거리 계산] 목표 거리: {target_distance_mm}mm ({target_distance_m:.3f}m)")
    print(f"[거리 계산] 계산식: {measured_gap_mm}mm - {OFFSET_MM}mm = {target_distance_mm}mm")
    
    return target_distance_m

# 카메라 초기화 (CSI 카메라 전용) - 안정성 및 성능 강화
print("=== CSI 카메라 초기화 시작 ===")

# CSI 카메라 초기화 (GStreamer 파이프라인 사용)
if current_platform == "Windows":
    print("❌ Windows 환경에서는 CSI 카메라를 지원하지 않습니다.")
    print("   Jetson Nano 환경에서만 실행 가능합니다.")
    exit(1)
else:
    # Jetson에서 CSI 카메라 사용 (GStreamer 파이프라인)
    print("Jetson 환경 - CSI 카메라 전용")
    
    # CSI 전면 카메라 (sensor-id=0) 초기화
    pipeline_front = gstreamer_pipeline(
        capture_width=FRAME_WIDTH, 
        capture_height=FRAME_HEIGHT, 
        display_width=FRAME_WIDTH, 
        display_height=FRAME_HEIGHT, 
        framerate=FPS, 
        flip_method=0, 
        sensor_id=1
    )
    
    print(f"전면 카메라 파이프라인: {pipeline_front}")
    cap_front = cv.VideoCapture(pipeline_front, cv.CAP_GSTREAMER)
    
    # CSI 후면 카메라 (sensor-id=1) 초기화
    pipeline_back = gstreamer_pipeline(
        capture_width=FRAME_WIDTH, 
        capture_height=FRAME_HEIGHT, 
        display_width=FRAME_WIDTH, 
        display_height=FRAME_HEIGHT, 
        framerate=FPS, 
        flip_method=0, 
        sensor_id=0
    )

    print(f"후면 카메라 파이프라인: {pipeline_back}")
    cap_back = cv.VideoCapture(pipeline_back, cv.CAP_GSTREAMER)
    
    # 카메라 연결 확인
    if not cap_front.isOpened():
        print("❌ CSI frontcam (sensor-id=0) 연결 실패")
        exit(1)
    else:
        print("✅ CSI frontcam (sensor-id=0) 연결 성공")
        
    if not cap_back.isOpened():
        print("⚠️ CSI backcam (sensor-id=1) 연결 실패 - 전면 카메라만 사용")
        cap_back = None
    else:
        print("✅ CSI backcam (sensor-id=1) 연결 성공")

if cap_front is None or not cap_front.isOpened():
    print("❌ 전방 카메라 초기 연결 실패")
    exit(1)

# CSI 카메라는 GStreamer 파이프라인에서 해상도가 이미 설정됨
print("✅ CSI 카메라 초기화 성공 - GStreamer 파이프라인 설정 사용")

# 전방 카메라 CSI 설정 적용
try:
    configure_csi_camera_settings(cap_front, "전방 카메라")
except Exception as e:
    print(f"전방 카메라 설정 실패: {e}")

# 후방 카메라 설정 (있는 경우)
if cap_back is not None and cap_back.isOpened():
    print("후방 카메라 설정 중...")
    # 후방 카메라 CSI 설정 적용
    try:
        configure_csi_camera_settings(cap_back, "후방 카메라")
    except Exception as e:
        print(f"후방 카메라 설정 실패: {e}")
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

# npy 파일 불러오기 - CSI 카메라용 캘리브레이션
camera_front_matrix = np.load(r"camera_test/calibration_result/camera_front_matrix.npy")
dist_front_coeffs = np.load(r"camera_test/calibration_result/dist_front_coeffs.npy")

# 보정 행렬과 왜곡 계수를 불러옵니다.
print("Loaded front camera matrix : \n", camera_front_matrix)
print("Loaded front distortion coefficients : \n", dist_front_coeffs)

# back camera 파일이 있는 경우만 로드
camera_back_matrix = None
dist_back_coeffs = None
if cap_back is not None:
    try:
        camera_back_matrix = np.load(r"camera_test/calibration_result/camera_back_matrix.npy")
        dist_back_coeffs = np.load(r"camera_test/calibration_result/dist_back_coeffs.npy")
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

final_target_distance = DEFAULT_ARUCO_DISTANCE  # 최종 목표 거리 초기화

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

                # 입차 시작: 차량 들어올리기 동작 (첫코드 시작부분)
                print("[Client] 차량 들어올리기 시작...")
                if serial_server is not None:
                    # 7번 명령 전 버퍼 클리어 (안전장치)
                    serial_server.reset_input_buffer()
                    
                    print("[Client] 7번 중앙정렬 후진 실패 - 기본 7번 명령으로 대체")
                        # 실패 시 기본 7번 명령 실행
                    serial_server.write(b"7")
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 시리얼 수신: '{recv}'")
                            if recv == "a":
                                print("[Client] 차량 들어올리기 완료!")
                                break
                            else : 
                                # 계속 대기
                                continue
                    
                    print("[Client] 들어올리기 후 차량 간격 데이터 수신 시작...")
                    
                    while True:
                        dynamic_target_distance = receive_vehicle_distance_data()
                        if dynamic_target_distance is not None:
                            print(f"[Client] 최종 차량과 로봇 간격: {dynamic_target_distance}mm ({dynamic_target_distance/10.0}cm)")
                            # 최종 간격 데이터를 바탕으로 복귀 시 사용할 거리 계산
                            final_target_distance = calculate_aruco_target_distance(dynamic_target_distance)
                            print(f"[Client] 복귀용 동적 ArUco 인식 거리: {final_target_distance:.3f}m")
                            break
                        else:
                            print("[Client] 최종 차량 간격 데이터 수신 실패 - 기본 거리 사용")
                            final_target_distance = DEFAULT_ARUCO_DISTANCE  # 기본값
                            break
                            time.sleep(0.1)

                    # 새로운: 중앙정렬 후진 with 7번 명령
                    # print("[Client] 7번 명령으로 중앙정렬 후진 시작 (마커10 기준)...")
                    # success = driving.command7_backward_with_sensor_control(
                    #     cap=cap_front,  # 전방 카메라 사용
                    #     marker_dict=marker_dict,
                    #     param_markers=param_markers,
                    #     camera_matrix=camera_front_matrix,
                    #     dist_coeffs=dist_front_coeffs,
                    #     serial_server=serial_server,
                    #     alignment_marker_id=10,  # 마커10 기준 중앙정렬
                    #     camera_direction="front"  # 전방 카메라 방향
                    # )
                    
                    # if success:
                    #     print("[Client] 7번 중앙정렬 후진 성공!")
                    #     # 내려놓기 완료 후 차량 간격 데이터 수신
                    #     print("[Client] 내려놓기 후 차량 간격 데이터 수신 시작...")
                    #     dynamic_target_distance = receive_vehicle_distance_data()
                    #     if dynamic_target_distance is not None:
                    #         print(f"[Client] 최종 차량과 로봇 간격: {dynamic_target_distance}mm ({dynamic_target_distance/10.0}cm)")
                    #     # 최종 간격 데이터를 바탕으로 복귀 시 사용할 거리 계산
                    #         final_target_distance = calculate_aruco_target_distance(dynamic_target_distance)
                    #         print(f"[Client] 복귀용 동적 ArUco 인식 거리: {final_target_distance:.3f}m")
                    #     else:
                    #         print("[Client] 최종 차량 간격 데이터 수신 실패 - 기본 거리 사용")
                    #         final_target_distance = DEFAULT_ARUCO_DISTANCE  # 기본값
                    #         break
                    # else:
                    #     print("[Client] 7번 중앙정렬 후진 실패 - 기본 7번 명령으로 대체")
                    #     # 실패 시 기본 7번 명령 실행
                    #     serial_server.write(b"7")
                    #     while True:
                    #         if serial_server.in_waiting:
                    #             recv = serial_server.read().decode()
                    #             print(f"[Client] 시리얼 수신: '{recv}'")
                    #             if recv == "a":
                    #                 print("[Client] 차량 들어올리기 완료!")

                    #                 # 들어올리기 완료 후 차량 간격 데이터 수신
                    #             print("[Client] 들어올리기 후 차량 간격 데이터 수신 시작...")
                    #             dynamic_target_distance = receive_vehicle_distance_data()
                    #             if dynamic_target_distance is not None:
                    #                 print(f"[Client] 최종 차량과 로봇 간격: {dynamic_target_distance}mm ({dynamic_target_distance/10.0}cm)")
                    #                 # 최종 간격 데이터를 바탕으로 복귀 시 사용할 거리 계산
                    #                 final_target_distance = calculate_aruco_target_distance(dynamic_target_distance)
                    #                 print(f"[Client] 복귀용 동적 ArUco 인식 거리: {final_target_distance:.3f}m")
                    #             else:
                    #                 print("[Client] 최종 차량 간격 데이터 수신 실패 - 기본 거리 사용")
                    #                 final_target_distance = DEFAULT_ARUCO_DISTANCE  # 기본값
                    #                 break
                    #         time.sleep(0.1)
                    
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

                # 예시: 첫 번째 마커까지 직진 (중앙정렬)
                print("[Client] 첫 번째 마커로 직진 시작 (마커10 중앙정렬)")
                if serial_server is not None:
                    serial_server.write(b"1")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                        target_marker_id=sector, direction="forward", 
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance, serial_server=serial_server)
                
                # 마커 인식 후 정지
                client_socket.sendall(f"sector_arrived,{sector},None,None\n".encode())
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(0.5)

                driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=sector, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, is_back_camera=False)

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
                            if timeout_count > 200:  # 20초 타임아웃
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
                            if timeout_count > 200:  # 20초 타임아웃
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
                driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                        target_marker_id=subzone, direction="forward", 
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance, serial_server=serial_server)
                if serial_server is not None:
                    serial_server.write(b"9")

                # subzone 도착 후 서버에 신호 전송
                print("[Client] subzone 도착 신호 전송")
                client_socket.sendall(f"subzone_arrived,{sector},{side},{subzone}\n".encode())
                time.sleep(0.5)

                # subzone 도착 후 로봇 초기화
                driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=subzone, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)

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
                            if timeout_count > 200:  # 20초 타임아웃
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
                            if timeout_count > 200:  # 20초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                print("subzone 회전 완료")
                driving.flush_camera(cap_front, 5)  # 카메라 플러시
                time.sleep(1)
                if serial_server is not None:
                    #driving.initialize_robot(cap_back, marker_dict, param_markers, marker_index=2, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, is_back_camera=True)
                    serial_server.write(b"9")
                
                # 간단한 후진 제어: 마커 1번 인식까지 후진 (중앙정렬)
                print("[Client] 마커 1번 인식까지 후진 시작... (마커10 중앙정렬)")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                
                # 뒷카메라로 마커 1번 인식 (동적 거리 사용) with 중앙정렬
                print(f"[Client] 동적 인식 거리 {final_target_distance:.3f}m 사용")
                if cap_back is not None:
                    driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                            target_marker_id=1, direction="backward", 
                                                            camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                            camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                            target_distance=0.15, serial_server=serial_server)
                    print("[Client] 뒷카메라로 마커 1번 인식 완료 (중앙정렬)")
                else:
                    # 뒷카메라가 없으면 에러 처리
                    print("❌ [ERROR] 뒷카메라가 연결되지 않았습니다!")
                    print("❌ [ERROR] 후진 동작을 수행할 수 없습니다.")
                    if serial_server is not None:
                        serial_server.write(b"9")  # 긴급 정지
                    client_socket.sendall(b"ERROR: Rear camera not available for backward movement\n")
                    continue
                
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                print("[Client] 마커 1번까지 후진 완료")
                
                time.sleep(1)  # 안정화 대기

                # driving.initialize_robot(cap_back, marker_dict, param_markers, marker_index=1, serial_server=serial_server, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs, is_back_camera=True)
                
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
                                
                                # 내려놓기 완료 후 차량 간격 데이터 수신
                                print("[Client] 내려놓기 후 차량 간격 데이터 수신 시작...")
                                dynamic_target_distance = receive_vehicle_distance_data()
                                if dynamic_target_distance is not None:
                                    print(f"[Client] 최종 차량과 로봇 간격: {dynamic_target_distance}mm ({dynamic_target_distance/10.0}cm)")
                                    # 최종 간격 데이터를 바탕으로 복귀 시 사용할 거리 계산
                                    final_target_distance = calculate_aruco_target_distance(dynamic_target_distance)
                                    print(f"[Client] 복귀용 동적 ArUco 인식 거리: {final_target_distance:.3f}m")
                                else:
                                    print("[Client] 최종 차량 간격 데이터 수신 실패 - 기본 거리 사용")
                                    final_target_distance = DEFAULT_ARUCO_DISTANCE  # 기본값
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
                
                # 먼저 마커 2번을 인식할 때까지 전진 (중앙정렬) ----------------탈출하는 부분도 살짝 문제가 있네..? 이걸 어카지 / 새로 만든 함수로 대체 필요
                driving.flush_camera(cap_back, 5) if cap_back is not None else None
                driving.flush_camera(cap_front, 5)
                print("[Client] 마커 2번 인식 중... (마커10 중앙정렬)")
                driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                        target_marker_id=2, direction="forward", 
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance-MARKER2_ARUCO_DISTANCE, serial_server=serial_server, opposite_camera=True)
                
                print("[Client] 마커 2번 인식 완료, 탈출 성공!")

                # 탈출 성공
                client_socket.sendall(f"subzone_arrived,{sector},{side},{subzone}\n".encode())

                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                    time.sleep(0.5)
                    # driving.initialize_robot(cap_back, marker_dict, param_markers, 2, serial_server, camera_back_matrix, dist_back_coeffs, is_back_camera=True)
                
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
                        if timeout_count > 200:  # 20초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                driving.flush_camera(cap_back, 5)  # 카메라 플러시
                driving.flush_camera(cap_front, 5)  # 카메라 플러시

                # 3. 두 번째 마커로 복귀 (후진하면서 뒷카메라로 인식, 중앙정렬)
                print("[Client] 두 번째 마커로 복귀 중... (후진, 뒷카메라 사용, 마커 0번 인식, 중앙정렬)")

                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작

                # 뒷카메라로 마커 0번 인식 (중앙정렬)
                if cap_back is not None:
                    driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                        target_marker_id=0, direction="backward", 
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance, serial_server=serial_server, opposite_camera=True)
                else:
                    print("❌ [ERROR] 뒷카메라가 연결되지 않았습니다!")
                    print("❌ [ERROR] 후진 복귀 동작을 수행할 수 없습니다.")
                    if serial_server is not None:
                        serial_server.write(b"9")  # 긴급 정지
                    client_socket.sendall(b"ERROR: Rear camera not available for backward return\n")
                    continue               
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                    client_socket.sendall(f"sector_arrived,{sector},None,None\n".encode()) # sector 도착
                    time.sleep(0.5)
                    driving.initialize_robot(cap_front, marker_dict, param_markers, 0, serial_server, camera_front_matrix, dist_front_coeffs, is_back_camera=False)
                
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
                        if timeout_count > 200:  # 20초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                # 5. 초기 위치로 복귀 (첫 번째 마커까지 후진하면서 뒷카메라로, 중앙정렬)
                print("[Client] 초기 위치로 복귀 중... (후진, 뒷카메라 사용, 마커 3번 인식, 중앙정렬)")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                # 뒷카메라로 마커 0번 인식 (중앙정렬)
                if cap_back is not None:
                    driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                            target_marker_id=0, direction="backward", 
                                                            camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                            camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                            target_distance=final_target_distance, serial_server=serial_server, opposite_camera=True)
                else:
                    print("❌ [ERROR] 뒷카메라가 연결되지 않았습니다!")
                    print("❌ [ERROR] 초기 위치 복귀를 위한 후진 동작을 수행할 수 없습니다.")
                    if serial_server is not None:
                        serial_server.write(b"9")  # 긴급 정지
                    client_socket.sendall(b"ERROR: Rear camera not available for return to start\n")
                    continue
                if serial_server is not None:
                    client_socket.sendall(f"starting_point,0,None,None\n".encode())
                    serial_server.write(b"9")  # 정지
                
                # 6. 최종 위치 조정 (동작 확인 후 수정 필요)
                print("[Client] 최종 대기 위치로 이동...(동작 확인 필요하여 일단 제외)")
                if serial_server is not None:
                     driving.initialize_robot(cap_front, marker_dict, param_markers, 0, serial_server, camera_front_matrix, dist_front_coeffs, is_back_camera=False)
                

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
                
                # 첫 번째 마커까지 직진 (중앙정렬)
                print("[Client] 첫 번째 마커로 직진 시작 (마커10 중앙정렬)")
                if serial_server is not None:
                    serial_server.write(b"1")
                driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                        target_marker_id=sector, direction="forward", 
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance, serial_server=serial_server)
                if serial_server is not None:
                    serial_server.write(b"9")
                    driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=sector, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, is_back_camera=False)
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
                            if timeout_count > 200:  # 20초 타임아웃
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
                            if timeout_count > 200:  # 20초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                print("sector 회전 완료")
                driving.flush_camera(cap_front, 5)
                time.sleep(0.5)
                if serial_server is not None:
                    serial_server.write(b"9")

                # 두 번째 마커까지 직진 (중앙정렬)
                if serial_server is not None:
                    serial_server.write(b"1")
                driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                        target_marker_id=subzone, direction="forward", 
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance, serial_server=serial_server)
                if serial_server is not None:
                    serial_server.write(b"9")
                    driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=subzone, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, is_back_camera=False)
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
                            if timeout_count > 200:  # 20초 타임아웃
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
                            if timeout_count > 200:  # 20초 타임아웃
                                print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                                break
                print("subzone 회전 완료")
                driving.flush_camera(cap_front, 5)
                time.sleep(0.5)
                if serial_server is not None:
                    serial_server.write(b"9")
                    # driving.initialize_robot(cap_back, marker_dict, param_markers, marker_index=2, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs, is_back_camera=True)

                # 3. 차량 들어올리기 (7번 명령으로 진입)
                print("[Client] 차량 들어올리기 시작...")
                if serial_server is not None:
                    
                    # 새로운: 중앙정렬 후진 with 7번 명령
                    print("[Client] 7번 명령으로 중앙정렬 후진 시작 (마커10 기준)...")
                    success = driving.command7_backward_with_sensor_control(
                        cap=cap_back,  # 후방 카메라 사용
                        marker_dict=marker_dict,
                        param_markers=param_markers,
                        camera_matrix=camera_back_matrix,
                        dist_coeffs=dist_back_coeffs,
                        serial_server=serial_server,
                        alignment_marker_id=10,  # 마커10 기준 중앙정렬
                        camera_direction="back"  # 후방 카메라
                    )
                    
                    if success:
                        print("[Client] 7번 중앙정렬 후진 성공!")
                        # 내려놓기 완료 후 차량 간격 데이터 수신
                        print("[Client] 내려놓기 후 차량 간격 데이터 수신 시작...")
                        dynamic_target_distance = receive_vehicle_distance_data()
                        if dynamic_target_distance is not None:
                            print(f"[Client] 최종 차량과 로봇 간격: {dynamic_target_distance}mm ({dynamic_target_distance/10.0}cm)")
                        # 최종 간격 데이터를 바탕으로 복귀 시 사용할 거리 계산
                            final_target_distance = calculate_aruco_target_distance(dynamic_target_distance)
                            print(f"[Client] 복귀용 동적 ArUco 인식 거리: {final_target_distance:.3f}m")
                        else:
                            print("[Client] 최종 차량 간격 데이터 수신 실패 - 기본 거리 사용")
                            final_target_distance = DEFAULT_ARUCO_DISTANCE  # 기본값
                            break

                    else:
                        print("[Client] 7번 중앙정렬 후진 실패 - 기본 7번 명령으로 대체")
                        # 실패 시 기본 7번 명령 실행
                        serial_server.write(b"7")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                print(f"[Client] 시리얼 수신: '{recv}'")
                                if recv == "a":
                                    print("[Client] 차량 들어올리기 완료!")
                                    break
                            time.sleep(0.1)
                    
                    # 들어올리기 완료 후 정지 및 안정화
                    serial_server.write(b"9")
                    time.sleep(3)
                    
                    # 시리얼 버퍼 클리어
                    serial_server.reset_input_buffer()
                    serial_server.reset_output_buffer()
                    
                    print("[Client] 시스템 안정화 완료, 복귀 시작")

                # 4. (차량 대기 위치)로 복귀 (입차와 동일한 복귀 로직)
                print("[Client] 차량 대기 위치로 복귀 시작...")
                
                # 주차 공간에서 나오기 (마커 0번과의 거리가 0.3m 이상이 될 때까지)
                print("[Client] 주차 공간에서 탈출 중... (마커 0번과의 거리가 0.3m 이상이 될 때까지)")
                if serial_server is not None:
                    serial_server.write(b"1")
                
                # 탈출 동작 구현
                driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                        target_marker_id=2, direction="forward", 
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance-MARKER2_ARUCO_DISTANCE, serial_server=serial_server, opposite_camera=True)
                if serial_server is not None:
                    serial_server.write(b"9")
                    driving.initialize_robot(cap_back, marker_dict, param_markers, 2, serial_server, camera_back_matrix, dist_back_coeffs, is_back_camera=True)
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
                        if timeout_count > 200:  # 20초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                # 두 번째 마커로 복귀 (후진, 뒷카메라, 중앙정렬)
                print("[Client] 두 번째 마커로 복귀 중... (후진, 뒷카메라 사용, 마커 0번 인식, 중앙정렬)")
                if serial_server is not None:
                    serial_server.write(b"2")
                if cap_back is not None:
                    driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                            target_marker_id=0, direction="backward", 
                                                            camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                            camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                            target_distance=final_target_distance, serial_server=serial_server, opposite_camera=True)
                else:
                    print("❌ [ERROR] 뒷카메라가 연결되지 않았습니다!")
                    print("❌ [ERROR] 후진 복귀 동작을 수행할 수 없습니다.")
                    if serial_server is not None:
                        serial_server.write(b"9")  # 긴급 정지
                    client_socket.sendall(b"ERROR: Rear camera not available for backward return\n")
                    continue
                if serial_server is not None:
                    serial_server.write(b"9")
                    driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=0, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
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
                        if timeout_count > 200:  # 20초 타임아웃
                            print("[Client] 회전 완료 신호 타임아웃 - 강제 진행")
                            break
                    time.sleep(0.5)
                
                # 첫 번째 마커로 복귀 (후진, 뒷카메라, 중앙정렬)
                print("[Client] 첫 번째 마커로 복귀 중... (후진, 뒷카메라 사용, 마커 3번 인식, 중앙정렬)")
                if serial_server is not None:
                    serial_server.write(b"2")
                if cap_back is not None:
                    driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                            target_marker_id=0, direction="backward", 
                                                            camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                            camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                            target_distance=final_target_distance, serial_server=serial_server, opposite_camera=True)
                else:
                    print("❌ [ERROR] 뒷카메라가 연결되지 않았습니다!")
                    print("❌ [ERROR] 후진 복귀 동작을 수행할 수 없습니다.")
                    if serial_server is not None:
                        serial_server.write(b"9")  # 긴급 정지
                    client_socket.sendall(b"ERROR: Rear camera not available for backward return\n")
                    continue
                if serial_server is not None:
                    serial_server.write(b"9")
                    driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=0, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)

                # 간단한 후진 제어: 마커 3번 인식까지 후진 (중앙정렬)
                print("[Client] 마커 3번 인식까지 후진 시작... (마커10 중앙정렬)")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                
                # 뒷카메라로 마커 3번 인식 (동적 거리 사용) with 중앙정렬
                print(f"[Client] 동적 인식 거리 {final_target_distance:.3f}m 사용")
                if cap_back is not None:
                    driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers,
                                                            target_marker_id=3, direction="backward", 
                                                            camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                            camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                            target_distance=final_target_distance, serial_server=serial_server, opposite_camera=True)
                    print("[Client] 뒷카메라로 마커 3번 인식 완료 (중앙정렬)")
                else:
                    # 뒷카메라가 없으면 에러 처리
                    print("❌ [ERROR] 뒷카메라가 연결되지 않았습니다!")
                    print("❌ [ERROR] 출차 후 대기공간 복귀를 위한 후진 동작을 수행할 수 없습니다.")
                    if serial_server is not None:
                        serial_server.write(b"9")  # 긴급 정지
                    client_socket.sendall(b"ERROR: Rear camera not available for return to waiting area\n")
                    continue
                
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                print("[Client] 마커 3번까지 후진 완료")

                driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index=3, serial_server=serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                
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
                                
                                # 내려놓기 완료 후 차량 간격 데이터 수신
                                print("[Client] 내려놓기 후 차량 간격 데이터 수신 시작...")
                                dynamic_target_distance = receive_vehicle_distance_data()
                                if dynamic_target_distance is not None:
                                    print(f"[Client] 최종 차량과 로봇 간격: {dynamic_target_distance}mm ({dynamic_target_distance/10.0}cm)")
                                    # 최종 간격 데이터를 바탕으로 복귀 시 사용할 거리 계산
                                    final_target_distance = calculate_aruco_target_distance(dynamic_target_distance)
                                    print(f"[Client] 복귀용 동적 ArUco 인식 거리: {final_target_distance:.3f}m")
                                else:
                                    print("[Client] 최종 차량 간격 데이터 수신 실패 - 기본 거리 사용")
                                    final_target_distance = DEFAULT_ARUCO_DISTANCE  # 기본값
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
                # 로봇 초기 위치까지 전진 (마커 0 인식, 중앙정렬)
                driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers,
                                                        target_marker_id=0, direction="forward",
                                                        camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                        camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                        target_distance=final_target_distance, serial_server=serial_server)
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                
                # 8. 로봇 초기 위치 정밀 정렬 (마커 17 기준으로 중앙+수직 정렬)
                print("[Client] 로봇 초기 위치 정밀 정렬...")
                if serial_server is not None:
                    driving.initialize_robot(cap_front, marker_dict, param_markers, 0, serial_server, camera_front_matrix, dist_front_coeffs, is_back_camera=False)
                
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
            # 기본 driving 명령도 중앙정렬 버전으로 교체 (마커 17번 기본 사용)
            driving.driving_with_marker10_alignment(cap_front, cap_back, marker_dict, param_markers, 
                                                    target_marker_id=17, direction="forward", 
                                                    camera_front_matrix=camera_front_matrix, dist_front_coeffs=dist_front_coeffs,
                                                    camera_back_matrix=camera_back_matrix, dist_back_coeffs=dist_back_coeffs,
                                                    target_distance=final_target_distance, serial_server=serial_server)
            client_socket.sendall(b"OK: driving with alignment\n")
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
