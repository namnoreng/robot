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

# 플랫폼 구분
current_platform = platform.system()

# 시리얼 통신 초기화 (윈도우/리눅스 분기)
if current_platform == "Windows":
    serial_port = "COM3"  # 실제 연결된 포트로 변경 필요
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
        else:
            print("Failed to open serial communication.")
    except serial.SerialException as e:
        print(f"Serial communication error: {e}")
        serial_server = None

# 카메라 초기화 (윈도우/리눅스 분기)
if current_platform == "Windows":
    cap_front = cv.VideoCapture(0, cv.CAP_DSHOW)
else:
    cap_front = cv.VideoCapture(0)
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap_front.set(cv.CAP_PROP_FPS, 30)
while not cap_front.isOpened():
    print("waiting for front camera")
    time.sleep(1)
print("front camera is opened")

# OpenCV 버전에 따라 ArUco 파라미터 생성 방식 분기
cv_version = cv.__version__.split(".")
if int(cv_version[0]) == 3:
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
else:
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters()

# 서버 소켓 초기화 (직접 입력)
host_input = input("Enter server IP (default: 0.0.0.0): ").strip()
port_input = input("Enter server port (default: 12345): ").strip()
HOST = host_input if host_input else '0.0.0.0'
PORT = int(port_input) if port_input else 12345

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print(f"[Server] Waiting for app connection... ({HOST}:{PORT})")
client_socket, addr = server_socket.accept()
print(f"[Server] App connected: {addr}")

try:
    while True:
        data = client_socket.recv(1024)
        if not data:
            print("[Server] App disconnected")
            break
        command = data.decode().strip()
        print(f"[App] Command received: {command}")

        # Execute action based on command
        if command == "find_empty_place":
            find_destination.DFS(find_destination.parking_lot)
            client_socket.sendall(b"OK: find_empty_place\n")
        elif command == "find_car":
            client_socket.sendall(b"Enter car number\n")
            car_number = client_socket.recv(1024).decode().strip()
            find_destination.find_car(find_destination.parking_lot, car_number)
            client_socket.sendall(f"OK: find_car {car_number}\n".encode())
        elif command == "detect_aruco":
            detect_aruco.start_detecting_aruco(cap_front, marker_dict, param_markers)
            client_socket.sendall(b"OK: detect_aruco\n")
        elif command == "driving":
            driving.driving(cap_front, marker_dict, param_markers)
            client_socket.sendall(b"OK: driving\n")
        elif command == "auto_driving":
            # Add implementation if needed
            client_socket.sendall(b"OK: auto_driving\n")
        elif command == "reset_position":
            driving.initialize_robot(cap_front, marker_dict, param_markers, 17, serial_server)
            client_socket.sendall(b"OK: reset_position\n")
        elif command == "stop":
            client_socket.sendall(b"OK: stop\n")
            break
        else:
            client_socket.sendall(b"Unknown command\n")
except Exception as e:
    print(f"[Server] Error: {e}")

client_socket.close()
server_socket.close()
cap_front.release()
cv.destroyAllWindows()

