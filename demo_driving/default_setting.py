import cv2 as cv
import numpy as np
import serial
import time

mode_state = {"default" : 0, "finding_path" : 1}  # 모드 종류 설정

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
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap_front.set(cv.CAP_PROP_FPS, 30)

cap_back = cv.VideoCapture(1)  # 후방 카메라
cap_back.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_back.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
cap_back.set(cv.CAP_PROP_FPS, 30)

# 카메라 연결 확인
while not cap_front.isOpened():
    print("waiting for front camera")
    time.sleep(1)

print("front camera is opened")

while not cap_back.isOpened():
    print("waiting for back camera")
    time.sleep(1)

print("back camera is opened")

# 커밋 잘 되는지 확인용 메세지






