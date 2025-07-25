# 기본적으로 필요한 모듈
import cv2 as cv
import numpy as np
import serial
import socket
import time
import platform
# ArUco import 제거 (segmentation fault 방지)

# 다른 모듈 불러오기
import find_destination
import detect_aruco_safe as detect_aruco  # 안전한 마커 탐지 시스템 사용
import driving

current_platform = platform.system()

mode_state = {"default" : 0, 
              "find_empty_place" : 1, 
              "find_car" : 2, 
              "detect_aruco" : 3, 
              "driving" : 4,
              "auto_driving" : 5,
              "reset_position" : 6,
              "stop": "stop"}  # 모드 종류 설정

mode = mode_state["default"]  # 초기 모드 설정

# 시리얼 통신 초기화 (플랫폼별 포트 설정)
if current_platform == 'Windows':
    serial_port = "COM3"
elif current_platform == 'Linux':
    serial_port = "/dev/ttyACM0"
else:
    serial_port = None

serial_server = None
if serial_port:
    try:
        serial_server = serial.Serial(serial_port, 115200)
        if serial_server.is_open:
            print(f"Serial communication is open. ({serial_port})")
        else:
            print("Failed to open serial communication.")
    except serial.SerialException as e:
        print(f"Serial communication error: {e}")
        serial_server = None

# # TCP/IP 소켓 통신 초기화
# try:
#     tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     tcp_server.bind(('0.0.0.0', 12345))  # 외부 장치 접속 허용
#     tcp_server.listen(1)
#     print("TCP server is listening on port 12345.")
    
#     client_socket, addr = tcp_server.accept()
#     print(f"Connection accepted from {addr}")
    
#     while True:
#         data = client_socket.recv(1024)
#         if not data:
#             break
#         print(f"Received: {data.decode()}")
#         client_socket.sendall(data)  # echo back

#     client_socket.close()

# except socket.error as e:
#     print(f"Socket error: {e}")
#     tcp_server = None


# 색상 마커 시스템 설정 (ArUco 대체)
print(f"Using OpenCV {cv.__version__}")
print("색상 마커 탐지 시스템 사용 (ArUco 대체)")

# 더미 변수 (기존 코드 호환성)
marker_dict = None
param_markers = None

print("마커 탐지 시스템 설정 완료")

# 카메라 초기화 (플랫폼별 백엔드 설정)
if current_platform == 'Windows':
    cap_front = cv.VideoCapture(0, cv.CAP_DSHOW)  # Windows는 DirectShow 사용
    cap_back = cv.VideoCapture(1, cv.CAP_DSHOW)   # 후방 카메라도 DirectShow
elif current_platform == 'Linux':
    cap_front = cv.VideoCapture(0, cv.CAP_V4L2)   # Linux는 V4L2 사용
    cap_back = cv.VideoCapture(1, cv.CAP_V4L2)    # 후방 카메라도 V4L2

print("카메라 설정 중...")
# 전방 카메라 설정
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap_front.set(cv.CAP_PROP_FPS, 30)

# 후방 카메라 설정
cap_back.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_back.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap_back.set(cv.CAP_PROP_FPS, 30)

# 카메라 연결 확인 (타임아웃 추가)
print("카메라 연결 확인 중...")

# 전방 카메라 확인
front_timeout = 0
while not cap_front.isOpened() and front_timeout < 10:  # 10초 타임아웃
    print("waiting for front camera")
    time.sleep(1)
    front_timeout += 1

if cap_front.isOpened():
    print("✅ front camera is opened")
else:
    print("❌ front camera 열기 실패 - 프로그램 종료")
    exit(1)

# 후방 카메라 확인
back_timeout = 0
while not cap_back.isOpened() and back_timeout < 10:  # 10초 타임아웃
    print("waiting for back camera")
    time.sleep(1)
    back_timeout += 1

if cap_back.isOpened():
    print("✅ back camera is opened")
else:
    print("⚠️  back camera 열기 실패 - front camera만 사용")
    cap_back.release()
    cap_back = None

return_message = b's'

while True:
    mode = int(input("모드 선택 (0: 기본, 1: 빈 공간 찾기, 2: 차량 찾기, 3: 아르코 마커 인식 하기\n" \
    "4: 아르코마 마커 거리 인식하기, 5: 목표 설정 및 주행 해보기, 6: 위치 초기화): "))
    if mode not in mode_state.values():
        print("잘못된 모드입니다. 다시 선택하세요.")
        continue
    elif mode == mode_state["default"]:
        print("기본 모드입니다.")
        while True:
            command = input("명령입력:")

            if command == "1":
                if serial_server:
                    serial_server.write(f"1".encode())
                    print("모드 1 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "2":
                if serial_server:
                    serial_server.write(f"2".encode())
                    print("모드 2 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "3":
                if serial_server:
                    serial_server.write(f"3".encode())
                    print("모드 3 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "4":
                if serial_server:
                    serial_server.write(f"4".encode())
                    print("모드 4 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "5":
                if serial_server:
                    serial_server.write(f"5".encode())
                    print("모드 5 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "6":
                if serial_server:
                    serial_server.write(f"6".encode())
                    print("모드 6 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "7":
                if serial_server:
                    serial_server.write(f"7".encode())
                    print("모드 7 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "8":
                if serial_server:
                    serial_server.write(f"8".encode())
                    print("모드 8 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
            elif command == "9":
                if serial_server:
                    serial_server.write(f"9".encode())
                    print("모드 9 전송")
                else:
                    print("시리얼 연결 없음 - 명령 무시")

            elif command == "exit":
                print("기본 모드 종료")
                break
            else:
                print("잘못된 명령입니다. 다시 입력하세요.")

    # 모드에 따라 동작 변경
    if mode == mode_state["find_empty_place"]:
        # 빈 공간 찾기 모드
        find_destination.DFS(find_destination.parking_lot)  # 빈 공간 찾기 알고리즘 호출

    elif mode == mode_state["find_car"]:
        # 차량 찾기 모드
        car_number = input("찾고자 하는 차량 번호를 입력하세요: ")
        find_destination.find_car(find_destination.parking_lot, car_number)

    elif mode == mode_state["detect_aruco"]:
        # 색상 마커 인식 모드 (ArUco 대체)
        detect_aruco.start_detecting_aruco()

    elif mode == mode_state["driving"]:
        # 주행모드
        driving.driving(cap_front, marker_dict, param_markers, marker_index = 1)

    elif mode == mode_state["auto_driving"]:
        print("코드 들어가는거 확인")
        car_number = input("주차할 차량 번호를 입력하세요: ")
        
        # 카메라 매트릭스 로드
        camera_front_matrix = np.load(r"camera_value/camera_front_matrix.npy")
        dist_front_coeffs = np.load(r"camera_value/dist_front_coeffs.npy")
        
        first_marker, turning_1, secondmarker, turning_2 = find_destination.DFS(find_destination.parking_lot)
        
        # 1. 첫 번째 마커까지 직진
        print("1. 첫 번째 마커까지 직진 시작")
        serial_server.write(b"1")
        driving.driving(cap_front, marker_dict, param_markers, first_marker, camera_front_matrix, dist_front_coeffs)
        serial_server.write(b"9")
        print("첫 번째 마커 도착")
        time.sleep(2)

        # 2. 좌표에 맞춰 회전
        print("2. 첫 번째 회전 시작")
        if turning_1 == "left":
            serial_server.write(b"3")
            print("좌회전")
        elif turning_1 == "right":
            serial_server.write(b"4")
            print("우회전")
        
        # 회전 완료 신호 대기
        while True:
            if serial_server.in_waiting:
                recv = serial_server.read().decode()
                if recv == "s":
                    break
        print("첫 번째 회전 완료")
        
        # 카메라 버퍼 플러시
        driving.flush_camera(cap_front, 5)
        time.sleep(2)
        
        # 3. 두 번째 마커까지 직진
        print("3. 두 번째 마커까지 직진 시작")
        serial_server.write(b"1")
        driving.driving(cap_front, marker_dict, param_markers, secondmarker, camera_front_matrix, dist_front_coeffs)
        serial_server.write(b"9")
        print("두 번째 마커 도착")
        time.sleep(2)

        # 4. 좌표에 반대로 회전 (주차 공간으로)
        print("4. 주차를 위한 회전 시작")
        if turning_2 == "left":
            serial_server.write(b"3")  # 주차 시 같은 방향
            print("주차용 좌회전")
        elif turning_2 == "right":
            serial_server.write(b"4")  # 주차 시 같은 방향
            print("주차용 우회전")
        
        # 회전 완료 신호 대기
        while True:
            if serial_server.in_waiting:
                recv = serial_server.read().decode()
                if recv == "s":
                    break
        print("주차용 회전 완료")
        time.sleep(2)
        
        # 5. 후진 (주차 공간으로)
        print("5. 후진 시작 (주차)")
        serial_server.write(b"2")  # 후진 명령
        time.sleep(3)  # 적절한 후진 시간 (조정 필요)
        serial_server.write(b"9")  # 정지
        print("후진 완료")
        
        # 6. 인식 후 종료 (주차 확인)
        print("6. 주차 완료 확인 중...")
        # 주차 완료 후 최종 마커 인식 또는 상태 확인
        detect_aruco.start_detecting_aruco()
        
        print("주차 완료!")
        
        # 주차 완료 후 차량 등록
        find_destination.park_car_at(find_destination.parking_lot, first_marker, turning_1, secondmarker, turning_2, car_number)
        print(f"차량 {car_number} 주차 등록 완료")
    

    elif mode == mode_state["reset_position"]:
        print("위치 초기화 모드 진입")
        driving.initialize_robot(cap_front, marker_dict, param_markers, 17,serial_server)

    elif mode == mode_state["stop"]:
        print("프로그램 종료")
        break
    
    else:
        print("잘못된 모드입니다. 다시 선택하세요.")