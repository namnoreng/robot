import cv2 as cv
import numpy as np
import serial
import time
import find_destination
import detect_aruco
import driving

print("serial 모듈 경로:", serial.__file__)

mode_state = {"default" : 0, "find_empty_place" : 1, "find_car" : 2, "detect_aruco" : 3, "driving" : 4}  # 모드 종류 설정

mode = mode_state["default"]  # 초기 모드 설정

# 시리얼 통신 초기화
try:
    serial_server = serial.Serial('COM3', 9600)  # Windows: COMx / Linux: '/dev/ttyUSB0'
    if serial_server.is_open:
        print("Serial communication is open.")
    else:
        print("Failed to open serial communication.")
except serial.SerialException as e:
    print(f"Serial communication error: {e}")
    serial_server = None  # 시리얼 객체를 None으로 설정하여 연결되지 않은 상태를 처리

# ArUco 마커 설정
marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
param_markers = cv.aruco.DetectorParameters()

# 카메라 초기화
cap_front = cv.VideoCapture(0)  # 전방 카메라
print(1)
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
print(2)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
print(3)
cap_front.set(cv.CAP_PROP_FPS, 30)
print(4)

# cap_back = cv.VideoCapture(1)  # 후방 카메라
# cap_back.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
# cap_back.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
# cap_back.set(cv.CAP_PROP_FPS, 30)

# 카메라 연결 확인
while not cap_front.isOpened():
    print("waiting for front camera")
    time.sleep(1)

print("front camera is opened")

# while not cap_back.isOpened():
#     print("waiting for back camera")
#     time.sleep(1)

# print("back camera is opened")

while True:
    mode = int(input("모드 선택 (0: 기본, 1: 빈 공간 찾기, 2: 차량 찾기, 3: 아르코 마커 인식 하기\n4: 아르코마 마커 거리 인식하기): "))
    if mode not in mode_state.values():
        print("잘못된 모드입니다. 다시 선택하세요.")
        continue
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