#!/usr/bin/env python3
"""
기본 설정 파일 - CSI 카메라 지원 버전
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
import find_destination
import detect_aruco
import driving

def gstreamer_pipeline(capture_width=640, capture_height=480, 
                      display_width=640, display_height=480, 
                      framerate=30, flip_method=0, sensor_id=0):
    """CSI 카메라용 GStreamer 파이프라인"""
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
    """CSI 카메라용 간단한 설정 함수"""
    print(f"=== {camera_name} CSI 설정 확인 ===")
    
    try:
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)  # 최소 버퍼로 지연 최소화
        print("✅ CSI 카메라 버퍼 설정 완료")
        
        width = cap.get(cv.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
        fps = cap.get(cv.CAP_PROP_FPS)
        
        print(f"현재 해상도: {width}x{height}")
        print(f"현재 FPS: {fps}")
        print("✅ CSI 카메라는 GStreamer 파이프라인 설정 사용")
        
    except Exception as e:
        print(f"⚠️ {camera_name} 설정 확인 중 오류: {e}")
    
    print("=" * (len(camera_name) + 20))

current_platform = platform.system()

mode_state = {"default" : 0, 
              "find_empty_place" : 1, 
              "find_car" : 2, 
              "detect_aruco" : 3, 
              "detect_distance" : 4,
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


# ArUco 마커 설정 (레거시 방식 사용)
print(f"Using OpenCV {cv.__version__}")
# 테스트 결과에 따라 레거시 DetectorParameters_create() 사용
marker_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_5X5_250)
param_markers = aruco.DetectorParameters_create()  # 레거시 방식 - 크래시 방지

print("ArUco 설정 완료 (레거시 DetectorParameters_create() 사용)")

# 카메라 초기화 (CSI 카메라 지원)
print("=== 카메라 초기화 시작 ===")

if current_platform == 'Windows':
    print("❌ Windows 환경에서는 CSI 카메라를 지원하지 않습니다.")
    print("   Jetson Nano 환경에서만 실행 가능합니다.")
    exit(1)
elif current_platform == 'Linux':
    print("Jetson 환경 - CSI 카메라 사용")
    
    # CSI 전면 카메라 (sensor-id=0) 초기화
    pipeline_front = gstreamer_pipeline(
        capture_width=640, capture_height=480, 
        display_width=640, display_height=480, 
        framerate=30, flip_method=0, sensor_id=1
    )
    cap_front = cv.VideoCapture(pipeline_front, cv.CAP_GSTREAMER)
    
    # CSI 후면 카메라 (sensor-id=1) 초기화  
    pipeline_back = gstreamer_pipeline(
        capture_width=640, capture_height=480, 
        display_width=640, display_height=480, 
        framerate=30, flip_method=0, sensor_id=0
    )
    cap_back = cv.VideoCapture(pipeline_back, cv.CAP_GSTREAMER)
    
    # 전면 카메라 연결 확인
    if cap_front.isOpened():
        print("✅ CSI front camera (sensor-id=0) 연결 성공")
        configure_csi_camera_settings(cap_front, "전면 카메라")
    else:
        print("❌ CSI front camera 연결 실패")
        cap_front = None
    
    # 후면 카메라 연결 확인
    if cap_back.isOpened():
        print("✅ CSI back camera (sensor-id=1) 연결 성공")
        configure_csi_camera_settings(cap_back, "후면 카메라")
    else:
        print("⚠️ CSI back camera 연결 실패 - 전면 카메라만 사용")
        cap_back = None

print("카메라 초기화 완료")

return_message = b's'

while True:
    mode = int(input("모드 선택 (0: 기본, 1: 빈 공간 찾기, 2: 차량 찾기, 3: 아르코 마커 인식 하기\n" \
    "4: 아르코마 마커 거리 인식하기, 5: 목표 설정 및 주행 해보기, 6: 위치 초기화): "))
    if mode not in mode_state.values():
        print("잘못된 모드입니다. 다시 선택하세요.")
        continue
    elif mode == mode_state["default"]:
        print("기본 모드입니다.")
        print("카메라 창에서 ArUco 마커를 실시간으로 확인하면서 조종하세요.")
        print("키보드 입력: 'q'로 종료, 다른 키는 시리얼로 전송됩니다.")
        
        # 카메라 화면과 ArUco 마커 인식을 실시간으로 표시
        while True:
            ret, frame = cap_back.read()
            if not ret:
                print("카메라에서 프레임을 읽을 수 없습니다.")
                break
            
            # ArUco 마커 검출
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, _ = aruco.detectMarkers(gray, marker_dict, parameters=param_markers)
            
            # 검출된 마커가 있으면 표시
            if ids is not None:
                # 마커 경계 그리기
                aruco.drawDetectedMarkers(frame, corners, ids)
                
                # 각 마커의 거리 정보 표시
                for i, marker_id in enumerate(ids.flatten()):
                    # 마커 중심점 계산
                    center_x = int(corners[i][0][:, 0].mean())
                    center_y = int(corners[i][0][:, 1].mean())
                    
                    # 마커 ID와 위치 정보 텍스트 표시
                    cv.putText(frame, f"ID: {marker_id}", 
                              (center_x - 30, center_y - 10), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv.putText(frame, f"({center_x}, {center_y})", 
                              (center_x - 40, center_y + 20), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            # 화면 표시
            cv.imshow('Robot Control with ArUco Detection', frame)
            
            # 키보드 입력 처리 (1ms 대기)
            key = cv.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("기본 모드 종료")
                break
            elif key != 255:  # 키가 눌린 경우 (255는 아무 키도 안 눌림)
                command = chr(key)
                # 시리얼로 명령 전송
                if serial_server:
                    serial_server.write(command.encode())
                    print(f"명령 '{command}' 전송 완료")
                else:
                    print("시리얼 연결 없음 - 명령 무시")
        
        # 창 닫기
        cv.destroyAllWindows()

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
        if cap_front is not None:
            detect_aruco.start_detecting_aruco(cap_front, marker_dict, param_markers)
        else:
            print("❌ 전면 카메라가 없어 ArUco 인식을 할 수 없습니다.")

    elif mode == mode_state["detect_distance"]:
        # 거리 측정 모드
        marker_id = int(input("측정할 마커 ID를 입력하세요: "))
        
        # 카메라 매트릭스 로드 - CSI 카메라용 캘리브레이션
        try:
            camera_front_matrix = np.load(r"camera_test/calibration_result/camera_front_matrix.npy")
            dist_front_coeffs = np.load(r"camera_test/calibration_result/dist_front_coeffs.npy")
            camera_back_matrix = np.load(r"camera_test/calibration_result/camera_back_matrix.npy")
            dist_back_coeffs = np.load(r"camera_test/calibration_result/dist_back_coeffs.npy")
            marker_length = 0.05  # 마커 크기 (미터)
            
            print(f"마커 ID {marker_id}와의 거리 측정 중... (ESC로 종료)")
            
            while True:
                ret, frame = cap_front.read()
                if not ret:
                    break
                
                # driving.py의 find_aruco_info 함수 사용 (csi_5x5_aruco 최적화 적용됨)
                distance, (x_angle, y_angle, z_angle), (center_x, center_y) = driving.find_aruco_info(
                    frame, marker_dict, param_markers, marker_id, 
                    camera_front_matrix, dist_front_coeffs, marker_length
                )
                
                if distance is not None:
                    # csi_5x5_aruco 방식: 거리 후처리 보정 (선택적)
                    # 필요시 거리 보정 계수 적용 (현재는 원본 값 사용)
                    corrected_distance = distance  # 보정 없음 (이미 왜곡 보정이 적용되어 정확함)
                    
                    # 화면에 거리 정보 표시 (cm 단위 추가)
                    distance_cm = corrected_distance * 100
                    cv.putText(frame, f"Distance: {corrected_distance:.3f}m ({distance_cm:.1f}cm)", 
                              (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv.putText(frame, f"Marker ID: {marker_id}", 
                              (10, 70), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                    cv.putText(frame, f"Angle Z: {z_angle:.1f} deg", 
                              (10, 110), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
                    # csi_5x5_aruco 방식: 추가 정보 표시
                    cv.putText(frame, f"Center: ({center_x}, {center_y})", 
                              (10, 150), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv.putText(frame, "CSI Optimized", 
                              (10, 190), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    print(f"[ID{marker_id}] Distance: {distance_cm:.1f}cm, Z-Angle: {z_angle:.1f}°, Center: ({center_x}, {center_y})")
                else:
                    cv.putText(frame, "Marker not found", 
                              (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                cv.imshow("Distance Measurement", frame)
                
                key = cv.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    break
            
            cv.destroyAllWindows()
                
        except Exception as e:
            print(f"오류 발생: {e}")

    elif mode == mode_state["auto_driving"]:
        print("코드 들어가는거 확인")
        
        # 전면 카메라 확인
        if cap_front is None:
            print("❌ 전면 카메라가 없어 자율주행을 할 수 없습니다.")
            continue
            
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
        detect_aruco.start_detecting_aruco(cap_front, marker_dict, param_markers)
        
        print("주차 완료!")
        
        # 주차 완료 후 차량 등록
        find_destination.park_car_at(find_destination.parking_lot, first_marker, turning_1, secondmarker, turning_2, car_number)
        print(f"차량 {car_number} 주차 등록 완료")
    

    elif mode == mode_state["reset_position"]:
        print("위치 초기화 모드 진입")
        if cap_front is not None:
            driving.initialize_robot(cap_front, marker_dict, param_markers, 17, serial_server)
        else:
            print("❌ 전면 카메라가 없어 위치 초기화를 할 수 없습니다.")

    elif mode == mode_state["stop"]:
        print("프로그램 종료")
        break
    
    else:
        print("잘못된 모드입니다. 다시 선택하세요.")