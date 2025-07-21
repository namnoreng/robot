# 기본적으로 필요한 모듈
import cv2 as cv
import numpy as np
import serial
import socket
import time
import platform
from cv2 import aruco

# 다른 모듈 불러오기
import find_destination
import detect_aruco
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

# 시리얼 통신 초기화
try:
    serial_server = serial.Serial('/dev/ttyACM0', 115200)  # Windows: COMx / Linux: '/dev/ttyUSB0'
    if serial_server.is_open:
        print("Serial communication is open.")
    else:
        print("Failed to open serial communication.")
except serial.SerialException as e:
    print(f"Serial communication error: {e}")
    serial_server = None  # 시리얼 객체를 None으로 설정하여 연결되지 않은 상태를 처리

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


# ArUco 마커 설정(os에 따라 다르게 설정)
if current_platform == 'Windows':
    marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
    param_markers = cv.aruco.DetectorParameters()
elif current_platform == 'Linux':
    marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()

# 카메라 초기화 (os에 따라 다르게 설정)
if current_platform == 'Windows':
    cap_front = cv.VideoCapture(0, cv.CAP_DSHOW)  # Windows는 DirectShow 사용
elif current_platform == 'Linux':
    cap_front = cv.VideoCapture(0)               # Linux는 백엔드 지정 없이 사용

print(1)
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
print(2)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
print(3)
cap_front.set(cv.CAP_PROP_FPS, 30)
print(4)



# cap_back = cv.VideoCapture(1)  # 후방 카메라
# print(1)
# cap_back.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
# print(2)
# cap_back.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
# print(3)
# cap_back.set(cv.CAP_PROP_FPS, 30)
# print(4)

# 카메라 연결 확인
while not cap_front.isOpened():
    print("waiting for front camera")
    time.sleep(1)

print("front camera is opened")

# while not cap_back.isOpened():
#     print("waiting for back camera")
#     time.sleep(1)

# print("back camera is opened")

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
                serial_server.write(f"1".encode())
                print("모드 1 전송")
            elif command == "2":
                serial_server.write(f"2".encode())
                print("모드 2 전송")
            elif command == "3":
                serial_server.write(f"3".encode())
                print("모드 3 전송")
                # return_message = serial_server.read_until(b'\n')
                # print(return_message.decode().strip())
            elif command == "4":
                serial_server.write(f"4".encode())
                print("모드 4 전송")
                # return_message = serial_server.read_until(b'\n')
                # print(return_message.decode().strip())
                
            elif command == "5":
                print("모드 5 전송")
                serial_server.write(f"5".encode())

            elif command == "6":
                print("모드 6 전송")
                serial_server.write(f"6".encode())

            elif command == "7":
                print("모드 7 전송")
                serial_server.write(f"7".encode())

            elif command == "8":
                print("모드 8 전송")
                serial_server.write(f"8".encode())

            elif command == "9":
                serial_server.write(f"9".encode())
                print("모드 9 전송")

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
        # 아르코 마커 인식 모드
        detect_aruco.start_detecting_aruco(cap_front, marker_dict, param_markers)

    elif mode == mode_state["driving"]:
        # 주행모드
        driving.driving(cap_front, marker_dict, param_markers)

    elif mode == mode_state["auto_driving"]:
        print("코드 들어가는거 확인")
        car_number = input("주차할 차량 번호를 입력하세요: ")
        first_marker, turning_1, secondmarker, turning_2 = find_destination.DFS(find_destination.parking_lot)  # 빈 공간 찾기 알고리즘 호출
        
        serial_server.write(f"1".encode())
        driving.driving(cap_front, marker_dict, param_markers, first_marker)
        serial_server.write(f"9".encode())
        print("first marker detected")
        # 이 부분 딜레이가 필요할듯?
        time.sleep(5)

        if(turning_1 == "left"):
            serial_server.write(f"3".encode())
            print("turning detected")

        elif(turning_1 == "right"):
            serial_server.write(f"4".encode())
            print("turning detected")
        # 이 명령 주고나서도 다 돌았는지 확인하기 위한 딜레이가 필요함

        while True:
            _, (_,_,z_angle),(_,_) = detect_aruco.find_aruco_info(cap_front, marker_dict, param_markers,first_marker,driving.camera_matrix, driving.dist_coeffs, driving.marker_length)
            if abs(z_angle) >= -0.5 and abs(z_angle) <= 0.5:
                serial_server.write(f"9".encode())
                print("turning complete")
                time.sleep(5)
                break
        
        serial_server.write(f"1".encode())
        time.sleep(1)
        driving.driving(cap_front, marker_dict, param_markers, secondmarker)
        serial_server.write(f"9".encode())
        print("second marker detected")

        time.sleep(5)
        if turning_2 == "left":
            serial_server.write(f"4".encode())
        elif turning_2 == "right":
            serial_server.write(f"3".encode())
        
        while True:
            _, (_,_,z_angle),(_,_) = detect_aruco.find_aruco_info(cap_front, marker_dict, param_markers, secondmarker, driving.camera_matrix, driving.dist_coeffs, driving.marker_length)
            if abs(z_angle) >= -1 and abs(z_angle) <= 1:
                serial_server.write(f"9".encode())
                print("turning complete")
                time.sleep(5)
                break
        
        print("arrived at destination")
        
        serial_server.write(f"9".encode())
        # 주차하는 코드인데 일단 주석처리 동일 테스트를 하기 위함
        # find_destination.park_car_at(find_destination.parking_lot, first_marker, turning, secondmarker, car_number)
    

    elif mode == mode_state["reset_position"]:
        print("위치 초기화 모드 진입")
        driving.initialize_robot(cap_front, marker_dict, param_markers, 17,serial_server)

    elif mode == mode_state["stop"]:
        print("프로그램 종료")
        break
    
    else:
        print("잘못된 모드입니다. 다시 선택하세요.")