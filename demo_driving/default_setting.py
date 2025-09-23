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
              "marker10_alignment" : 7,
              "opposite_camera_test" : 8,
              "command7_test" : 9,
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

# 전역 카메라 매트릭스 및 왜곡 계수 변수
camera_front_matrix = None
dist_front_coeffs = None
camera_back_matrix = None
dist_back_coeffs = None

def load_camera_calibration():
    """카메라 캘리브레이션 파일을 로드하는 함수"""
    global camera_front_matrix, dist_front_coeffs, camera_back_matrix, dist_back_coeffs
    
    print("=== 카메라 캘리브레이션 파일 로드 ===")
    
    # 전방 카메라 캘리브레이션 로드
    try:
        camera_front_matrix = np.load(r"camera_test/calibration_result/camera_front_matrix.npy")
        dist_front_coeffs = np.load(r"camera_test/calibration_result/dist_front_coeffs.npy")
        print("✅ 전방 카메라 캘리브레이션 로드 완료")
    except FileNotFoundError:
        print("⚠️ 전방 카메라 캘리브레이션 파일을 찾을 수 없습니다.")
        camera_front_matrix = None
        dist_front_coeffs = None
    
    # 후방 카메라 캘리브레이션 로드
    try:
        camera_back_matrix = np.load(r"camera_test/calibration_result/camera_back_matrix.npy")
        dist_back_coeffs = np.load(r"camera_test/calibration_result/dist_back_coeffs.npy")
        print("✅ 후방 카메라 캘리브레이션 로드 완료")
    except FileNotFoundError:
        print("⚠️ 후방 카메라 캘리브레이션 파일을 찾을 수 없습니다.")
        camera_back_matrix = None
        dist_back_coeffs = None
    
    # 로드 결과 요약
    front_status = "OK" if camera_front_matrix is not None else "Missing"
    back_status = "OK" if camera_back_matrix is not None else "Missing"
    print(f"📊 캘리브레이션 상태: 전방={front_status}, 후방={back_status}")
    
    return camera_front_matrix is not None or camera_back_matrix is not None

# 프로그램 시작 시 캘리브레이션 파일 로드
calibration_loaded = load_camera_calibration()

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

cap_front = None
cap_back = None

if current_platform == 'Windows':
    print("⚠️ Windows 환경에서는 CSI 카메라를 지원하지 않습니다.")
    print("   캘리브레이션 데이터만 로드하고, 카메라 없이 일부 기능만 사용 가능합니다.")
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

# 시스템 상태 요약
print("\n=== 시스템 상태 요약 ===")
print(f"📷 전방 카메라: {'연결됨' if cap_front else '연결 안됨'}")
print(f"📷 후방 카메라: {'연결됨' if cap_back else '연결 안됨'}")
print(f"📊 전방 캘리브레이션: {'로드됨' if camera_front_matrix is not None else '없음'}")
print(f"📊 후방 캘리브레이션: {'로드됨' if camera_back_matrix is not None else '없음'}")
print(f"🔌 시리얼 통신: {'연결됨' if serial_server else '연결 안됨'}")
print("=== 초기화 완료 ===\n")

return_message = b's'

while True:
    mode = int(input("모드 선택 (0: 기본, 1: 빈 공간 찾기, 2: 차량 찾기, 3: 아르코 마커 인식 하기\n" \
    "4: 아르코마 마커 거리 인식하기, 5: 목표 설정 및 주행 해보기, 6: 위치 초기화, 7: 10번 마커 중앙정렬 주행\n" \
    "8: 반대 카메라 테스트, 9: 7번 명령 + 적외선 센서 테스트): "))
    if mode not in mode_state.values():
        print("잘못된 모드입니다. 다시 선택하세요.")
        continue
    elif mode == mode_state["default"]:
        print("기본 모드입니다.")
        print("카메라 창에서 ArUco 마커를 실시간으로 확인하면서 조종하세요.")
        print("키보드 입력: 'q'로 종료, 다른 키는 시리얼로 전송됩니다.")
        
        # 전역 캘리브레이션 변수 사용
        if camera_front_matrix is not None and dist_front_coeffs is not None:
            print("✅ 전역 캘리브레이션 사용 - 왜곡 보정 적용")
        else:
            print("⚠️ 캘리브레이션이 없습니다. 왜곡 보정 없이 진행합니다.")
        
        # 카메라 화면과 ArUco 마커 인식을 실시간으로 표시
        while True:
            ret, frame = cap_front.read()
            if not ret:
                print("카메라에서 프레임을 읽을 수 없습니다.")
                break
            
            # 왜곡 보정 적용 (캘리브레이션 파일이 있는 경우)
            if camera_front_matrix is not None and dist_front_coeffs is not None:
                frame_display = cv.undistort(frame, camera_front_matrix, dist_front_coeffs)
            else:
                frame_display = frame.copy()
            
            # ArUco 마커 검출 (원본 프레임에서)
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            corners, ids, _ = aruco.detectMarkers(gray, marker_dict, parameters=param_markers)
            
            # 검출된 마커가 있으면 표시 (표시용 프레임에)
            if ids is not None:
                # 마커 경계 그리기 (왜곡 보정된 프레임에 표시하기 위해 좌표 변환)
                if camera_front_matrix is not None and dist_front_coeffs is not None:
                    # 왜곡 보정된 프레임에 마커 그리기
                    aruco.drawDetectedMarkers(frame_display, corners, ids)
                else:
                    # 왜곡 보정이 없으면 원본 프레임에 그리기
                    aruco.drawDetectedMarkers(frame_display, corners, ids)
                
                # 각 마커의 정보 표시
                for i, marker_id in enumerate(ids.flatten()):
                    # 마커 중심점 계산
                    center_x = int(corners[i][0][:, 0].mean())
                    center_y = int(corners[i][0][:, 1].mean())
                    
                    # 마커 ID와 위치 정보 텍스트 표시 (왜곡 보정된 프레임에)
                    cv.putText(frame_display, f"ID: {marker_id}", 
                              (center_x - 30, center_y - 10), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv.putText(frame_display, f"({center_x}, {center_y})", 
                              (center_x - 40, center_y + 20), 
                              cv.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            # 왜곡 보정 상태 표시
            if camera_front_matrix is not None and dist_front_coeffs is not None:
                cv.putText(frame_display, "Undistortion: ON", 
                          (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                cv.putText(frame_display, "Undistortion: OFF", 
                          (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # 화면 표시 (왜곡 보정된 프레임)
            cv.imshow('Robot Control with ArUco Detection', frame_display)
            
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
        
        # 전역 캘리브레이션 변수 사용
        if camera_front_matrix is None or dist_front_coeffs is None:
            print("❌ 전방 카메라 캘리브레이션이 없어 거리 측정을 할 수 없습니다.")
            continue
            
        marker_length = 0.05  # 마커 크기 (미터)
        
        print(f"마커 ID {marker_id}와의 거리 측정 중... (ESC로 종료)")
        
        while True:
            ret, frame = cap_front.read()
            if not ret:
                break
                
                # csi_5x5_aruco 방식: 화면 표시용 프레임에도 왜곡 보정 적용
                frame_display = cv.undistort(frame, camera_front_matrix, dist_front_coeffs)
                
                # driving.py의 find_aruco_info 함수 사용 (csi_5x5_aruco 최적화 적용됨)
                distance, (x_angle, y_angle, z_angle), (center_x, center_y) = driving.find_aruco_info(
                    frame, marker_dict, param_markers, marker_id, 
                    camera_front_matrix, dist_front_coeffs, marker_length
                )
                
                if distance is not None:
                    # csi_5x5_aruco 방식: 거리 후처리 보정 (선택적)
                    # 필요시 거리 보정 계수 적용 (현재는 원본 값 사용)
                    corrected_distance = distance  # 보정 없음 (이미 왜곡 보정이 적용되어 정확함)
                    
                    # 화면에 거리 정보 표시 (cm 단위 추가) - 왜곡 보정된 프레임에 표시
                    distance_cm = corrected_distance * 100
                    cv.putText(frame_display, f"Distance: {corrected_distance:.3f}m ({distance_cm:.1f}cm)", 
                              (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv.putText(frame_display, f"Marker ID: {marker_id}", 
                              (10, 70), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                    cv.putText(frame_display, f"Angle Z: {z_angle:.1f} deg", 
                              (10, 110), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
                    # csi_5x5_aruco 방식: 추가 정보 표시
                    cv.putText(frame_display, f"Center: ({center_x}, {center_y})", 
                              (10, 150), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv.putText(frame_display, "CSI Optimized + Undistorted", 
                              (10, 190), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    print(f"[ID{marker_id}] Distance: {distance_cm:.1f}cm, Z-Angle: {z_angle:.1f}°, Center: ({center_x}, {center_y})")
                else:
                    cv.putText(frame_display, "Marker not found",
                              (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                cv.imshow("Distance Measurement", frame_display)
                
            key = cv.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
        
        cv.destroyAllWindows()

    elif mode == mode_state["auto_driving"]:
        print("코드 들어가는거 확인")
        
        # 전면 카메라 확인
        if cap_front is None:
            print("❌ 전면 카메라가 없어 자율주행을 할 수 없습니다.")
            continue
            
        # 전역 캘리브레이션 확인
        if camera_front_matrix is None or dist_front_coeffs is None:
            print("❌ 전방 카메라 캘리브레이션이 없어 자율주행을 할 수 없습니다.")
            continue
            
        car_number = input("주차할 차량 번호를 입력하세요: ")
        
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
        
        if cap_front is None:
            print("❌ 전면 카메라가 없어 위치 초기화를 할 수 없습니다.")
            continue
        
        if serial_server is None:
            print("❌ 시리얼 통신이 연결되지 않아 로봇을 제어할 수 없습니다.")
            continue
        
        # 사용자로부터 마커 인덱스 입력 받기
        try:
            marker_index = int(input("초기화할 마커 ID를 입력하세요 (기본값: 17): ") or "17")
            if marker_index < 0 or marker_index > 250:  # ArUco 마커 범위 확인
                print("❌ 잘못된 마커 ID입니다. 0-250 사이의 값을 입력하세요.")
                continue
        except ValueError:
            print("❌ 숫자를 입력하세요.")
            continue
        
        print(f"마커 {marker_index}번을 기준으로 위치 초기화를 시작합니다...")
        
        # 위치 초기화 실행
        driving.initialize_robot(cap_front, marker_dict, param_markers, marker_index, serial_server)
        
        # 동작 종료 안내
        print(f"마커 {marker_index}번을 기준으로 위치 초기화가 완료되었습니다.")
    
        # 안전을 위해 정지
        serial_server.write(b"9")
        print("로봇 정지")

    elif mode == mode_state["marker10_alignment"]:
        print("10번 마커 중앙정렬 주행 모드 진입")
        
        # 전면 카메라 확인
        if cap_front is None:
            print("❌ 전면 카메라가 없어 주행을 할 수 없습니다.")
            continue
            
        # 시리얼 통신 확인
        if serial_server is None:
            print("❌ 시리얼 통신이 연결되지 않아 로봇을 제어할 수 없습니다.")
            continue
        
        # 사용자 입력
        try:
            target_marker = int(input("찾을 목표 마커 번호를 입력하세요: "))
            target_distance = float(input("목표 거리를 입력하세요 (m, 기본값 0.15): ") or "0.15")
            direction = input("이동 방향을 입력하세요 (forward/backward, 기본값 forward): ").strip() or "forward"
            
            if direction not in ["forward", "backward"]:
                print("❌ 잘못된 방향입니다. forward 또는 backward만 입력 가능합니다.")
                continue
                
        except ValueError:
            print("❌ 잘못된 입력입니다. 숫자를 입력해주세요.")
            continue
        
        # 전역 캘리브레이션 변수 확인
        if camera_front_matrix is None or dist_front_coeffs is None:
            print("❌ 전방 카메라 캘리브레이션이 없어 주행을 할 수 없습니다.")
            continue
            
        if camera_back_matrix is None or dist_back_coeffs is None:
            print("⚠️ 후방 카메라 캘리브레이션이 없습니다 - 전방 카메라만 사용")
        else:
            print("✅ 전방/후방 카메라 캘리브레이션 모두 사용 가능")
        
        print(f"설정 정보:")
        print(f"  - 목표 마커: {target_marker}번")
        print(f"  - 목표 거리: {target_distance}m")
        print(f"  - 이동 방향: {direction}")
        print(f"  - 정렬 기준: 10번 마커")
        print("주행 시작! (ESC 키로 중단 가능)")
        
        # 진행 방향에 따른 초기 이동 명령
        if direction == "forward":
            serial_server.write(b"1")  # 직진 시작
            print("직진 시작")
        else:
            serial_server.write(b"2")  # 후진 시작
            print("후진 시작")
        
        # 10번 마커 중앙정렬 주행 실행
        success = driving.driving_with_marker10_alignment(
            cap_front, cap_back, marker_dict, param_markers, 
            target_marker_id=target_marker,
            camera_front_matrix=camera_front_matrix, 
            dist_front_coeffs=dist_front_coeffs,
            camera_back_matrix=camera_back_matrix,
            dist_back_coeffs=dist_back_coeffs,
            target_distance=target_distance,
            serial_server=serial_server,
            direction=direction
        )
        
        # 결과 출력
        if success:
            print("목표 마커에 성공적으로 도달했습니다!")
        else:
            print("주행이 중단되었습니다.")
        
        # 안전을 위해 정지
        serial_server.write(b"9")
        print("로봇 정지")

    elif mode == mode_state["opposite_camera_test"]:
        print("=== 반대 카메라 테스트 모드 ===")
        print("진행방향과 반대되는 카메라를 사용하여 중앙정렬 주행을 테스트합니다.")
        
        try:
            target_marker = int(input("목표 마커 ID를 입력하세요 (1-19): "))
            if target_marker < 1 or target_marker > 19:
                print("❌ 잘못된 마커 ID입니다. 1-19 사이의 값을 입력하세요.")
                continue
        except ValueError:
            print("❌ 숫자를 입력하세요.")
            continue
        
        try:
            target_distance = float(input("목표 거리를 입력하세요 (m, 예: 0.15): "))
            if target_distance <= 0:
                print("❌ 거리는 0보다 큰 값이어야 합니다.")
                continue
        except ValueError:
            print("❌ 올바른 숫자를 입력하세요.")
            continue
        
        direction_input = input("이동 방향을 선택하세요 (f: 직진, b: 후진): ").lower()
        if direction_input == 'f':
            direction = "forward"
            print("직진 + 후방 카메라 모드 (반대 카메라)")
        elif direction_input == 'b':
            direction = "backward"
            print("후진 + 전방 카메라 모드 (반대 카메라)")
        else:
            print("잘못된 입력입니다. 'f' 또는 'b'를 입력하세요.")
            continue
        
        print(f"목표: 마커 {target_marker}, 거리 {target_distance}m, 방향 {direction}")
        print("3초 후 시작합니다... (ESC 키로 중단 가능)")
        time.sleep(3)
        
        # 초기 동작 명령 전송
        if serial_server:
            if direction == "forward":
                print("[반대 카메라 테스트] 직진 명령 전송")
                serial_server.write(b"1")  # 직진
            elif direction == "backward":
                print("[반대 카메라 테스트] 후진 명령 전송")
                serial_server.write(b"2")  # 후진
            time.sleep(0.5)  # 초기 동작 시작 대기
        
        # 반대 카메라 테스트 실행
        success = driving.driving_with_marker10_alignment(
            cap_front, cap_back, marker_dict, param_markers,
            target_marker_id=target_marker,
            camera_front_matrix=camera_front_matrix,
            dist_front_coeffs=dist_front_coeffs,
            camera_back_matrix=camera_back_matrix,
            dist_back_coeffs=dist_back_coeffs,
            target_distance=target_distance,
            serial_server=serial_server,
            direction=direction,
            opposite_camera=True  # 반대 카메라 사용
        )
        
        # 결과 출력
        if success:
            print("반대 카메라 테스트 성공! 목표 마커에 도달했습니다!")
        else:
            print("반대 카메라 테스트가 중단되었습니다.")
        
        # 안전을 위해 정지
        serial_server.write(b"9")
        print("로봇 정지")

    elif mode == mode_state["command7_test"]:
        print("=== 7번 명령 + 적외선 센서 테스트 모드 ===")
        print("7번 명령으로 후진하면서 적외선 센서 기반 제어를 테스트합니다.")
        print("동작 순서:")
        print("1. 7번 명령으로 후진 + 마커 중앙정렬")
        print("2. 적외선 센서가 차량 바퀴 인식 시 'l' 신호 수신 → 즉시 정지")
        print("3. 'a' 신호 대기 → 7번 내부 루틴 완료")
        
        try:
            alignment_marker = int(input("중앙정렬 기준 마커 ID를 입력하세요 (기본값: 10): ") or "10")
            if alignment_marker < 0 or alignment_marker > 19:
                print("❌ 잘못된 마커 ID입니다. 0-19 사이의 값을 입력하세요.")
                continue
        except ValueError:
            print("❌ 숫자를 입력하세요.")
            continue
        
        # 카메라 선택
        camera_choice = input("사용할 카메라 선택 (1: 전방카메라, 2: 후방카메라, 기본값: 2): ") or "2"
        if camera_choice == "1":
            use_camera = cap_front
            camera_matrix = camera_front_matrix
            dist_coeffs = dist_front_coeffs
            camera_name = "전방카메라"
        elif camera_choice == "2":
            if cap_back is not None and camera_back_matrix is not None:
                use_camera = cap_back
                camera_matrix = camera_back_matrix
                dist_coeffs = dist_back_coeffs
                camera_name = "후방카메라"
            else:
                print("❌ 후방카메라가 설정되지 않아 전방카메라를 사용합니다.")
                use_camera = cap_front
                camera_matrix = camera_front_matrix
                dist_coeffs = dist_front_coeffs
                camera_name = "전방카메라 (대체)"
        else:
            print("❌ 잘못된 선택입니다. 후방카메라를 기본값으로 사용합니다.")
            use_camera = cap_back if cap_back is not None else cap_front
            camera_matrix = camera_back_matrix if camera_back_matrix is not None else camera_front_matrix
            dist_coeffs = dist_back_coeffs if dist_back_coeffs is not None else dist_front_coeffs
            camera_name = "후방카메라" if cap_back is not None else "전방카메라 (대체)"
        
        print(f"설정: 마커 {alignment_marker} 기준 중앙정렬, {camera_name} 사용")
        print("3초 후 시작합니다... (ESC 키로 중단 가능)")
        time.sleep(3)
        
        # 7번 명령 + 적외선 센서 기반 후진 테스트 실행
        success = driving.command7_backward_with_sensor_control(
            cap=use_camera,
            marker_dict=marker_dict,
            param_markers=param_markers,
            camera_matrix=camera_matrix,
            dist_coeffs=dist_coeffs,
            serial_server=serial_server,
            alignment_marker_id=alignment_marker
        )
        
        # 결과 출력
        if success:
            print("✅ 7번 명령 + 적외선 센서 테스트 성공!")
            print("   - 'l' 신호로 정지")
            print("   - 'a' 신호로 7번 루틴 완료")
        else:
            print("❌ 7번 명령 + 적외선 센서 테스트가 중단되었습니다.")
        
        # 안전을 위해 정지
        serial_server.write(b"9")
        print("로봇 정지")

    elif mode == mode_state["stop"]:
        print("프로그램 종료")
        break
    
    else:
        print("잘못된 모드입니다. 다시 선택하세요.")