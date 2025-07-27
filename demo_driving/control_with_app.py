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

# 카메라 초기화 (윈도우/리눅스 분기)
if current_platform == "Windows":
    cap_front = cv.VideoCapture(0, cv.CAP_DSHOW)
    cap_back = cv.VideoCapture(1, cv.CAP_DSHOW)
else:
    # Jetson Nano에서 V4L2 백엔드 사용
    cap_front = cv.VideoCapture(0, cv.CAP_V4L2)
    cap_back = cv.VideoCapture(1, cv.CAP_V4L2)
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap_front.set(cv.CAP_PROP_FPS, 30)

if cap_back is not None:
    cap_back.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
    cap_back.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
    cap_back.set(cv.CAP_PROP_FPS, 30)

# 카메라가 열릴 때까지 대기 (타임아웃 추가)
front_timeout = 0
while not cap_front.isOpened() and front_timeout < 10:  # 10초 타임아웃
    print("waiting for front camera")
    time.sleep(1)
    front_timeout += 1

if cap_front.isOpened():
    print("front camera is opened")
else:
    print("❌ front camera 열기 실패 - 프로그램 종료")
    exit(1)

back_timeout = 0
while not cap_back.isOpened() and back_timeout < 10:  # 10초 타임아웃
    print("waiting for back camera")
    time.sleep(1)
    back_timeout += 1

if cap_back.isOpened():
    print("back camera is opened")
else:
    print("⚠️  back camera 열기 실패 - front camera만 사용")
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

# OpenCV 버전에 따라 ArUco 파라미터 생성 방식 분기
cv_version = cv.__version__.split(".")
if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
else:
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()

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
                    timeout_count = 0
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            print(f"[Client] 시리얼 수신: '{recv}'")
                            if recv == "a":
                                print("[Client] 차량 들어올리기 완료!")
                                break
                            else:
                                print(f"[Client] 예상치 못한 신호: '{recv}' - 계속 대기...")
                        
                        # 타임아웃 방지 (10초)
                        timeout_count += 1
                        if timeout_count > 100:  # 10초 (0.1초 * 100)
                            print("[Client] 'a' 신호 대기 타임아웃 - 강제 진행")
                            break
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
                driving.driving(cap_front, marker_dict, param_markers, marker_index=sector, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(2)

                # 방향에 따라 회전
                if side == "left":
                    if serial_server is not None:
                        serial_server.write(b"3")
                        # 회전 완료 신호(s) 대기
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                elif side == "right":
                    if serial_server is not None:
                        serial_server.write(b"4")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                print("sector 회전 완료 ")
                driving.flush_camera(cap_front, 5)  # 카메라 플러시
                time.sleep(2)
                if serial_server is not None:
                    serial_server.write(b"9")

                if serial_server is not None:
                    serial_server.write(b"1")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=subzone, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(2)

                # 방향에 따라 회전
                if direction == "left":
                    if serial_server is not None:
                        serial_server.write(b"4")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                elif direction == "right":
                    if serial_server is not None:
                        serial_server.write(b"3")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                    else:
                        print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                print("subzone 회전 완료")
                driving.flush_camera(cap_front, 5)  # 카메라 플러시
                time.sleep(2)
                if serial_server is not None:
                    serial_server.write(b"9")

                # 복합 후진 제어 함수 호출 (명시적으로 마커 1, 2 사용)
                success = driving.advanced_parking_control(
                    cap_front, cap_back, marker_dict, param_markers,
                    camera_front_matrix, dist_front_coeffs,
                    camera_back_matrix, dist_back_coeffs, serial_server,
                    back_marker_id=1, front_marker_id=2
                )
                
                if success:
                    print("[Client] 복합 후진 제어 성공")
                else:
                    print("[Client] 복합 후진 제어 실패 - 기본 후진으로 대체")
                    # 실패 시 기본 후진
                    if serial_server is not None:
                        serial_server.write(b"2")
                        time.sleep(2)  # 2초간 후진
                        serial_server.write(b"9")
                
                time.sleep(1)  # 안정화 대기
                
                # 주차공간 도착 후 차량 내려놓기
                print("[Client] 차량 내려놓기 시작...")
                if serial_server is not None:
                    serial_server.write(b"8")  # 차량 내려놓기 명령
                    print("[Client] 차량 내려놓기 동작 중...")
                    time.sleep(3)  # 3초간 내려놓기 동작 대기
                    print("[Client] 차량 내려놓기 완료!")
                else:
                    print("[Client] 시리얼 통신이 연결되지 않았습니다.")
                    time.sleep(3)  # 시리얼이 없어도 3초 대기
                
                # 주차 완료 신호를 서버에 전송
                print(f"[Client] 주차 완료: {sector},{side},{subzone},{direction},{car_number}")
                client_socket.sendall(f"DONE,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                
                # 주차 완료 후 제자리로 복귀
                print("[Client] 제자리 복귀 시작...")
                
                # 1. 주차 공간에서 나오기 (마커 0번까지 전진)
                print("[Client] 주차 공간에서 탈출 중... (마커 0번 인식까지)")
                if serial_server is not None:
                    serial_server.write(b"1")  # 전진 시작
                # 마커 0번을 인식할 때까지 전진
                driving.driving(cap_back, marker_dict, param_markers, marker_index=0, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                    time.sleep(1)
                
                # 2. 돌아갈 방향으로 회전 (주차할 때와 반대)
                print("[Client] 복귀를 위한 회전...")
                if serial_server is not None:
                    if direction == "left":
                        serial_server.write(b"3")  # 원래 왔던 방향과 반대로
                    elif direction == "right":
                        serial_server.write(b"4")
                    
                    # 회전 완료 신호 대기
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            if recv == "s":
                                break
                    time.sleep(1)
                
                # 3. 두 번째 마커로 복귀 (후진하면서 뒷카메라로 인식)
                print("[Client] 두 번째 마커로 복귀 중... (후진, 뒷카메라 사용, 마커 0번 인식)")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                # 뒷카메라로 마커 0번 인식
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=0, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                else:
                    print("[Client] 뒷카메라가 없어 전방카메라로 대체")
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=0, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                    time.sleep(1)
                
                # 4. 첫 번째 회전 방향과 반대로 회전
                print("[Client] 첫 번째 마커 방향으로 회전...")
                if serial_server is not None:
                    if side == "left":
                        serial_server.write(b"4")  # 왔던 방향과 반대
                    elif side == "right":
                        serial_server.write(b"3")
                    
                    # 회전 완료 신호 대기
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            if recv == "s":
                                break
                    time.sleep(1)
                
                # 5. 초기 위치로 복귀 (첫 번째 마커까지 후진하면서 뒷카메라로)
                print("[Client] 초기 위치로 복귀 중... (후진, 뒷카메라 사용, 마커 0번 인식)")
                if serial_server is not None:
                    serial_server.write(b"2")  # 후진 시작
                # 뒷카메라로 마커 3번 인식
                if cap_back is not None:
                    driving.driving(cap_back, marker_dict, param_markers, marker_index=3, camera_matrix=camera_back_matrix, dist_coeffs=dist_back_coeffs)
                else:
                    print("[Client] 뒷카메라가 없어 전방카메라로 대체")
                    driving.driving(cap_front, marker_dict, param_markers, marker_index=3, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")  # 정지
                
                # 6. 최종 위치 조정 (마커 17로 이동 - 초기 대기 위치)
                print("[Client] 최종 대기 위치로 이동...")
                if serial_server is not None:
                    driving.initialize_robot(cap_front, marker_dict, param_markers, 17, serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                
                print("[Client] 제자리 복귀 완료!")
                
                # 필요하다면 추가 주행/회전/정지 등 구현

                client_socket.sendall(b"OK: PARK command received\n")
            except Exception as e:
                print(f"[Client] PARK 명령 파싱 오류: {e}")
                client_socket.sendall(b"ERROR: PARK command parse error\n")
        elif command.startswith("OUT"):
            # 예: "OUT,1234" (차량번호)
            try:
                _, car_number = command.split(",")
                print(f"[Client] 출차 요청 차량번호: {car_number}")
                
                # 1. 차량 위치 조회 (parking_status.json에서 검색)
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
                
                # 2. 차량 위치로 이동 (입차와 동일한 경로)
                print(f"[Client] 차량 위치로 이동 시작: {sector}, {side}, {subzone}, {direction}")
                
                # 첫 번째 마커까지 직진
                print("[Client] 첫 번째 마커로 직진 시작")
                if serial_server is not None:
                    serial_server.write(b"1")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=sector, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(2)

                # 방향에 따라 회전
                if side == "left":
                    if serial_server is not None:
                        serial_server.write(b"3")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                elif side == "right":
                    if serial_server is not None:
                        serial_server.write(b"4")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                print("sector 회전 완료")
                driving.flush_camera(cap_front, 5)
                time.sleep(2)
                if serial_server is not None:
                    serial_server.write(b"9")

                # 두 번째 마커까지 직진
                if serial_server is not None:
                    serial_server.write(b"1")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=subzone, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                time.sleep(2)

                # 방향에 따라 회전
                if direction == "left":
                    if serial_server is not None:
                        serial_server.write(b"4")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                elif direction == "right":
                    if serial_server is not None:
                        serial_server.write(b"3")
                        while True:
                            if serial_server.in_waiting:
                                recv = serial_server.read().decode()
                                if recv == "s":
                                    break
                print("subzone 회전 완료")
                driving.flush_camera(cap_front, 5)
                time.sleep(2)
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
                
                # 주차 공간에서 나오기 (마커 0번까지 전진)
                print("[Client] 주차 공간에서 탈출 중... (마커 0번 인식까지)")
                if serial_server is not None:
                    serial_server.write(b"1")
                driving.driving(cap_front, marker_dict, param_markers, marker_index=0, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                if serial_server is not None:
                    serial_server.write(b"9")
                    time.sleep(1)
                
                # 돌아갈 방향으로 회전
                print("[Client] 복귀를 위한 회전...")
                if serial_server is not None:
                    if direction == "left":
                        serial_server.write(b"3")
                    elif direction == "right":
                        serial_server.write(b"4")
                    
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            if recv == "s":
                                break
                    time.sleep(1)
                
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
                    time.sleep(1)
                
                # 첫 번째 회전 방향과 반대로 회전
                print("[Client] 첫 번째 마커 방향으로 회전...")
                if serial_server is not None:
                    if side == "left":
                        serial_server.write(b"4")
                    elif side == "right":
                        serial_server.write(b"3")
                    
                    while True:
                        if serial_server.in_waiting:
                            recv = serial_server.read().decode()
                            if recv == "s":
                                break
                    time.sleep(1)
                
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
                
                # 5. 차량 대기 장소로 이동 (기존 복합 후진 제어 함수 활용)
                print("[Client] 차량 대기 장소로 이동... (복합 후진 제어)")
                
                # 기존 advanced_parking_control 함수 사용 (마커 17, 3 사용)
                success = driving.advanced_parking_control(
                    cap_front, cap_back, marker_dict, param_markers,
                    camera_front_matrix, dist_front_coeffs,
                    camera_back_matrix, dist_back_coeffs, serial_server,
                    back_marker_id=17, front_marker_id=3
                )
                
                if success:
                    print("[Client] 차량 대기 장소 도착 성공")
                else:
                    print("[Client] 복합 후진 제어 실패 - 기본 후진으로 대체")
                    # 실패 시 기본 후진으로 마커 17까지 이동
                    if serial_server is not None:
                        serial_server.write(b"2")  # 후진
                    driving.driving(cap_back if cap_back is not None else cap_front, marker_dict, param_markers, marker_index=17, 
                                  camera_matrix=camera_back_matrix if cap_back is not None else camera_front_matrix, 
                                  dist_coeffs=dist_back_coeffs if cap_back is not None else dist_front_coeffs)
                    if serial_server is not None:
                        serial_server.write(b"9")  # 정지
                
                # 6. 차량 내려놓기
                print("[Client] 차량 내려놓기 시작...")
                if serial_server is not None:
                    serial_server.write(b"8")  # 차량 내려놓기 명령
                    print("[Client] 차량 내려놓기 동작 중...")
                    time.sleep(3)
                    print("[Client] 차량 내려놓기 완료!")
                
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
                    driving.initialize_robot(cap_front, marker_dict, param_markers, 17, serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
                
                print(f"[Client] 출차 완료: {car_number}")
                
                # 주차 상태에서 차량 정보 제거
                try:
                    parking_data[f"sector_{sector}"][side][f"subzone_{subzone}"][direction] = {
                        "occupied": False,
                        "car_number": None
                    }
                    with open("parking_status.json", "w", encoding="utf-8") as f:
                        json.dump(parking_data, f, ensure_ascii=False, indent=2)
                    print(f"[Client] 주차 상태 업데이트 완료")
                except Exception as e:
                    print(f"[Client] 주차 상태 업데이트 실패: {e}")
                
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
                driving.initialize_robot(cap_front, marker_dict, param_markers, 17, serial_server, camera_matrix=camera_front_matrix, dist_coeffs=dist_front_coeffs)
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

client_socket.close()
cap_front.release()
cv.destroyAllWindows()
