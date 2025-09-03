#!/usr/bin/env python3
"""
Driving 모듈 - camera_test 최적화 적용
- 개선된 거리 측정 알고리즘 적용
- 터미널 거리값 출력 형식 통일 (cm 단위)
- 예외 처리 강화
- camera_test/csi_5x5_aruco_distance_fixed.py 방식 적용
"""

import cv2
import cv2.aruco as aruco
import numpy as np
import serial
import time
import platform

# 플랫폼 확인
current_platform = platform.system()

# 마커 크기 설정 - camera_test에서 검증된 최적화 값
# 실제 측정값과 비교하여 조정: 0.05 * (실제거리/측정거리) ≈ 0.029
marker_length = 0.029  # camera_test에서 검증된 보정 값 (m)

# OpenCV 버전 및 플랫폼에 따라 ArUco 파라미터 생성 방식 분기
cv_version = cv2.__version__.split(".")
print(f"OpenCV 버전: {cv2.__version__}, 플랫폼: {current_platform}")

# 플랫폼별 분기 처리 (Jetson의 경우 특별 처리)
if current_platform == "Linux":  # Jetson Nano/Xavier 등
    print("Jetson (Linux) 환경 - DetectorParameters_create() 사용")
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
    
elif int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
    print("OpenCV 3.2.x 이하 - 레거시 방식 사용")
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
else:
    print("OpenCV 4.x (Windows) - 신규 방식 사용")
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters()

def flush_camera(cap, num=5):
    for _ in range(num):
        cap.read()

def initialize_robot(cap, aruco_dict, parameters, marker_index, serial_server, camera_matrix, dist_coeffs, is_back_camera=False):
    FRAME_CENTER_X = 320   # 640 x 480 해상도 기준
    FRAME_CENTER_Y = 240
    CENTER_TOLERANCE = 30  # 중앙 허용 오차 (픽셀)
    ANGLE_TOLERANCE = 5    # 각도 허용 오차 (도)
    
    # 마커 위치 추적 변수
    last_marker_position = None  # 마지막으로 본 마커 위치 (center_x, center_y)
    marker_lost_count = 0  # 마커를 놓친 프레임 수
    MAX_LOST_FRAMES = 10  # 마커를 놓쳤을 때 최대 대기 프레임
    
    camera_type = "뒷카메라" if is_back_camera else "전방카메라"
    print(f"[Initialize] 마커 {marker_index} 기준 로봇 초기화 시작 ({camera_type})")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("카메라 프레임을 읽지 못했습니다.")
            continue

        result = find_aruco_info(
            frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length
        )
        distance, (x_angle, y_angle, z_angle), (center_x, center_y) = result

        if distance is not None:
            # 마커를 찾았을 때
            marker_lost_count = 0  # 카운터 리셋
            last_marker_position = (center_x, center_y)  # 위치 업데이트
            
            dx = center_x - FRAME_CENTER_X
            angle_error = z_angle
            distance_cm = distance * 100

            print(f"[ID{marker_index}] Initialize Distance: {distance_cm:.1f}cm, Z-Angle: {angle_error:.1f}°, Center: ({center_x}, {center_y}) ({camera_type})")

            # 1. 회전값 먼저 맞추기
            if abs(angle_error) > ANGLE_TOLERANCE:
                if angle_error > 0:
                    print(f"[Initialize] 좌회전 ({camera_type})")
                    serial_server.write('3'.encode())
                else:
                    print(f"[Initialize] 우회전 ({camera_type})")
                    serial_server.write('4'.encode())
                time.sleep(0.1)  # 명령 간 딜레이
                continue  # 회전이 맞을 때까지 중앙값 동작으로 넘어가지 않음

            # 2. 회전이 맞으면 중앙값 맞추기 (뒷카메라일 때는 좌우 명령 반대)
            if abs(dx) > CENTER_TOLERANCE:
                if dx > 0:
                    if is_back_camera:
                        print(f"[Initialize] 왼쪽으로 이동 ({camera_type} - 반대 명령)")
                        serial_server.write('5'.encode())  # 뒷카메라: 반대 명령
                    else:
                        print(f"[Initialize] 오른쪽으로 이동 ({camera_type})")
                        serial_server.write('6'.encode())  # 전방카메라: 정상 명령
                else:
                    if is_back_camera:
                        print(f"[Initialize] 오른쪽으로 이동 ({camera_type} - 반대 명령)")
                        serial_server.write('6'.encode())  # 뒷카메라: 반대 명령
                    else:
                        print(f"[Initialize] 왼쪽으로 이동 ({camera_type})")
                        serial_server.write('5'.encode())  # 전방카메라: 정상 명령
                time.sleep(0.1)  # 명령 간 딜레이
                continue  # 중앙이 맞을 때까지 반복

            # 3. 둘 다 맞으면 정지
            print(f"[Initialize] 초기화 완료: 중앙+수직 ({camera_type})")
            serial_server.write('9'.encode())  # 정지 명령
            break

        else:
            # 마커를 찾지 못했을 때
            marker_lost_count += 1
            print(f"[Initialize] 마커를 찾지 못했습니다. ({marker_lost_count}/{MAX_LOST_FRAMES}) ({camera_type})")
            
            if marker_lost_count >= MAX_LOST_FRAMES and last_marker_position is not None:
                # 마커를 일정 시간 이상 놓쳤고, 마지막 위치 정보가 있을 때
                last_x, last_y = last_marker_position
                
                print(f"[Initialize] 마커 재탐색 중... 마지막 위치: ({last_x}, {last_y}) ({camera_type})")
                
                # 마지막 위치를 기준으로 이동 방향 결정 (뒷카메라일 때는 좌우 명령 반대)
                if last_x < FRAME_CENTER_X - 100:  # 마커가 왼쪽에 있었음
                    if is_back_camera:
                        print(f"[Initialize] 마커가 왼쪽에 있었음 - 오른쪽으로 이동 ({camera_type} - 반대 명령)")
                        serial_server.write('6'.encode())  # 뒷카메라: 반대 명령
                    else:
                        print(f"[Initialize] 마커가 왼쪽에 있었음 - 왼쪽으로 이동 ({camera_type})")
                        serial_server.write('5'.encode())  # 전방카메라: 정상 명령
                elif last_x > FRAME_CENTER_X + 100:  # 마커가 오른쪽에 있었음
                    if is_back_camera:
                        print(f"[Initialize] 마커가 오른쪽에 있었음 - 왼쪽으로 이동 ({camera_type} - 반대 명령)")
                        serial_server.write('5'.encode())  # 뒷카메라: 반대 명령
                    else:
                        print(f"[Initialize] 마커가 오른쪽에 있었음 - 오른쪽으로 이동 ({camera_type})")
                        serial_server.write('6'.encode())  # 전방카메라: 정상 명령
                elif last_y < FRAME_CENTER_Y - 100:  # 마커가 위쪽에 있었음
                    print(f"[Initialize] 마커가 위쪽에 있었음 - 전진 ({camera_type})")
                    serial_server.write('1'.encode())  # 전진
                elif last_y > FRAME_CENTER_Y + 100:  # 마커가 아래쪽에 있었음
                    print(f"[Initialize] 마커가 아래쪽에 있었음 - 후진 ({camera_type})")
                    serial_server.write('2'.encode())  # 후진
                else:
                    # 중앙 근처에서 사라진 경우 - 약간 후진해서 시야 확보
                    print(f"[Initialize] 마커가 중앙에서 사라짐 - 후진하여 시야 확보 ({camera_type})")
                    serial_server.write('2'.encode())  # 후진
                
                time.sleep(0.5)  # 이동 후 잠시 대기
                serial_server.write('9'.encode())  # 정지
                marker_lost_count = 0  # 카운터 리셋
                
            elif marker_lost_count >= MAX_LOST_FRAMES * 2:
                # 너무 오래 못 찾으면 정지
                print(f"[Initialize] 마커를 찾을 수 없어 초기화를 중단합니다. ({camera_type})")
                serial_server.write('9'.encode())  # 정지 명령
                break
            else:
                # 잠시 정지하고 다시 시도
                serial_server.write('9'.encode())  # 정지 명령

        time.sleep(0.1)  # 프레임 처리 딜레이
        #cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()

# 직진 아르코마커 인식
def driving(cap, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, target_distance=0.4):
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # find_aruco_info 함수로 정보 추출
        distance, (x_angle, y_angle, z_angle), (center_x, center_y) = find_aruco_info(
            frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length
        )

        # 정보가 있으면 출력 및 동작
        if distance is not None:
            distance_cm = distance * 100
            print(f"[ID{marker_index}] Distance: {distance_cm:.1f}cm, Z-Angle: {z_angle:.1f}°, Center: ({center_x}, {center_y})")

            # 시각화
            cv2.putText(
                frame,
                f"ID: {marker_index} Distance: {distance:.3f} m",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            # 원하는 거리 이내에 들어오면 종료
            if distance < target_distance:
                break

        #cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()

def find_aruco_info(frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length):
    """
    개선된 ArUco 마커 거리 계산 (camera_test 버전 적용)
    
    Args:
        frame: 입력 이미지 (BGR)
        aruco_dict: ArUco 딕셔너리
        parameters: ArUco 파라미터
        marker_index: 찾고자 하는 마커 ID
        camera_matrix: 카메라 매트릭스
        dist_coeffs: 왜곡 계수
        marker_length: 마커 실제 길이(m)
    
    Returns:
        (distance, (x_angle, y_angle, z_angle), (center_x, center_y)) 
        또는 (None, (None, None, None), (None, None))
    """
    if camera_matrix is None or dist_coeffs is None:
        return None, (None, None, None), (None, None)
    
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None:
            for i in range(len(ids)):
                if ids[i][0] == marker_index:
                    # 포즈 추정 (OpenCV 버전 호환성 처리)
                    cv_version = cv2.__version__.split(".")
                    if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
                        # OpenCV 3.2.x 이하
                        rvecs, tvecs = cv2.aruco.estimatePoseSingleMarkers(
                            np.array([corners[i]]), marker_length, camera_matrix, dist_coeffs
                        )
                    else:
                        # OpenCV 3.3.x 이상 또는 4.x
                        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                            np.array([corners[i]]), marker_length, camera_matrix, dist_coeffs
                        )
                    
                    distance = np.linalg.norm(tvecs[0][0])

                    # 회전 행렬 및 각도
                    rotation_matrix, _ = cv2.Rodrigues(rvecs[0][0])
                    sy = np.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
                    singular = sy < 1e-6

                    if not singular:
                        x_angle = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
                        y_angle = np.arctan2(-rotation_matrix[2, 0], sy)
                        z_angle = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
                    else:
                        x_angle = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
                        y_angle = np.arctan2(-rotation_matrix[2, 0], sy)
                        z_angle = 0

                    x_angle = np.degrees(x_angle)
                    y_angle = np.degrees(y_angle)
                    z_angle = np.degrees(z_angle)

                    # 중심점 좌표 계산
                    c = corners[i].reshape(4, 2)
                    center_x = int(np.mean(c[:, 0]))
                    center_y = int(np.mean(c[:, 1]))

                    return distance, (x_angle, y_angle, z_angle), (center_x, center_y)
        
        # 해당 마커를 찾지 못함
        return None, (None, None, None), (None, None)
        
    except Exception as e:
        print(f"거리 계산 오류: {e}")
        return None, (None, None, None), (None, None)

def advanced_parking_control(cap_front, cap_back, aruco_dict, parameters, 
                           camera_front_matrix, dist_front_coeffs,
                           camera_back_matrix, dist_back_coeffs, serial_server,
                           back_marker_id=1, front_marker_id=2):
    """
    복합 후진 제어: 후방카메라 마커 인식 + 전방카메라 마커 실시간 중앙정렬
    
    Args:
        cap_front: 전방 카메라
        cap_back: 후방 카메라
        aruco_dict: ArUco 딕셔너리
        parameters: ArUco 파라미터
        camera_front_matrix: 전방 카메라 매트릭스
        dist_front_coeffs: 전방 카메라 왜곡 계수
        camera_back_matrix: 후방 카메라 매트릭스  
        dist_back_coeffs: 후방 카메라 왜곡 계수
        serial_server: 시리얼 통신 객체
        back_marker_id: 후방 카메라로 인식할 마커 번호 (기본값: 1)
        front_marker_id: 전방 카메라로 중앙정렬할 마커 번호 (기본값: 2)
    """
    print(f"[Driving] 복합 후진 제어 시작 (후방: 마커{back_marker_id} 인식, 전방: 마커{front_marker_id} 실시간 중앙정렬)")
    
    if serial_server is not None:
        serial_server.write(b"2")  # 후진 시작
    else:
        print("[Driving] 시리얼 통신이 연결되지 않았습니다.")
        return False

    FRAME_CENTER_X = 640  # 1280x720 해상도 기준 중앙
    CENTER_TOLERANCE = 30  # 중앙 허용 오차 (픽셀) - 정밀하게
    TARGET_DISTANCE = 0.3  # 후방 마커 목표 거리 (30cm)
    
    current_movement = None  # 현재 이동 상태 추적 ('left', 'right', 'backward', None)

    try:
        while True:
            # 후방카메라로 지정된 마커 체크 (주 조건)
            back_marker_found = False
            if cap_back is not None and camera_back_matrix is not None:
                ret_back, frame_back = cap_back.read()
                if ret_back:
                    back_distance, _, _ = find_aruco_info(
                        frame_back, aruco_dict, parameters, back_marker_id, 
                        camera_back_matrix, dist_back_coeffs, marker_length
                    )
                    if back_distance is not None:
                        back_distance_cm = back_distance * 100
                        print(f"[ID{back_marker_id}] 후방 Distance: {back_distance_cm:.1f}cm")
                        if back_distance < TARGET_DISTANCE:
                            back_marker_found = True
            
            # 전방카메라로 지정된 마커 실시간 중앙정렬
            target_movement = 'backward'  # 기본값은 후진
            if cap_front is not None:
                ret_front, frame_front = cap_front.read()
                if ret_front:
                    # 지정된 마커 탐지 및 중앙정렬
                    gray_front = cv2.cvtColor(frame_front, cv2.COLOR_BGR2GRAY)
                    corners, ids, _ = cv2.aruco.detectMarkers(gray_front, aruco_dict, parameters=parameters)
                    
                    if ids is not None:
                        closest_marker_center = None
                        closest_distance = float('inf')
                        
                        for i, marker_id in enumerate(ids):
                            if marker_id[0] == front_marker_id:  # 지정된 마커만 처리
                                # 마커까지의 거리 계산
                                distance, _, _ = find_aruco_info(
                                    frame_front, aruco_dict, parameters, front_marker_id, 
                                    camera_front_matrix, dist_front_coeffs, marker_length
                                )
                                
                                if distance is not None and distance < closest_distance:
                                    distance_cm = distance * 100
                                    print(f"[ID{front_marker_id}] 전방 Distance: {distance_cm:.1f}cm")
                                    
                                    # 마커 중심 계산
                                    c = corners[i].reshape(4, 2)
                                    center_x = int(np.mean(c[:, 0]))
                                    closest_marker_center = center_x
                                    closest_distance = distance
                        
                        if closest_marker_center is not None:
                            # 가장 가까운 마커의 중심을 기준으로 계산
                            dx = closest_marker_center - FRAME_CENTER_X
                            
                            print(f"[Driving] 가장 가까운 마커{front_marker_id} 거리: {closest_distance:.3f}m, 중심: {closest_marker_center:.1f}, 오차: {dx:.1f}")
                            
                            # 중앙정렬이 필요한 경우만 좌우 이동
                            if abs(dx) > CENTER_TOLERANCE:
                                if dx > 0:  # 마커가 오른쪽에 있으면 오른쪽으로 이동
                                    target_movement = 'right'
                                else:  # 마커가 왼쪽에 있으면 왼쪽으로 이동
                                    target_movement = 'left'
                            else:
                                # 중앙에 정렬됨 - 후진만 진행
                                print(f"[Driving] 마커{front_marker_id} 중앙 정렬됨 (오차: {dx:.1f}px)")
            
            # 메인 종료 조건: 후방 마커가 충분히 가까워졌을 때
            if back_marker_found:
                print(f"[Driving] 후방 마커{back_marker_id}에 충분히 접근 - 후진 완료")
                break
            
            # 시리얼 명령 실행 (이전 동작과 다를 때만)
            if target_movement != current_movement and serial_server is not None:
                if target_movement == 'left':
                    print(f"[Driving] 왼쪽으로 이동 (마커{front_marker_id} 중앙정렬)")
                    serial_server.write(b"5")
                    current_movement = 'left'
                elif target_movement == 'right':
                    print(f"[Driving] 오른쪽으로 이동 (마커{front_marker_id} 중앙정렬)")
                    serial_server.write(b"6")
                    current_movement = 'right'
                elif target_movement == 'backward':
                    print("[Driving] 후진 진행")
                    serial_server.write(b"2")
                    current_movement = 'backward'
            
            # 프레임 처리 딜레이
            time.sleep(0.05)  # 50ms 딜레이 (카메라 프레임 처리용)

    except Exception as e:
        print(f"[Driving] 복합 후진 제어 오류: {e}")
        return False
    
    finally:
        # 후진 완료 후 정지
        if serial_server is not None:
            serial_server.write(b"9")
        print("[Driving] 복합 후진 제어 완료")
    
    return True

def escape_from_parking(cap, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, target_distance=0.3):
    """
    주차공간에서 탈출하는 함수 - 마커와의 거리가 target_distance보다 클 때까지 전진
    
    Parameters:
    - cap: 카메라 객체
    - aruco_dict: ArUco 딕셔너리
    - parameters: ArUco 파라미터
    - marker_index: 탈출 기준 마커 ID
    - camera_matrix: 카메라 행렬
    - dist_coeffs: 왜곡 계수
    - target_distance: 목표 거리 (이 거리보다 멀어지면 탈출 완료)
    """
    print(f"[Escape] 주차공간 탈출 시작 - 마커 {marker_index}와의 거리가 {target_distance}m 이상이 될 때까지 전진")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[Escape] 카메라 프레임 읽기 실패")
            break

        # ArUco 마커 검출
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None:
            for i in range(len(ids)):
                if ids[i][0] == marker_index:
                    # 마커 발견 - 거리 계산
                    cv_version = cv2.__version__.split(".")
                    if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
                        rvecs, tvecs = cv2.aruco.estimatePoseSingleMarkers(
                            np.array([corners[i]]), marker_length, camera_matrix, dist_coeffs
                        )
                    else:
                        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                            np.array([corners[i]]), marker_length, camera_matrix, dist_coeffs
                        )
                    
                    distance = np.linalg.norm(tvecs[0][0])
                    print(f"[Escape] 마커 {marker_index} 거리: {distance:.3f}m (목표: {target_distance}m 이상)")
                    
                    # 마커와의 거리가 목표 거리보다 크면 탈출 완료
                    if distance > target_distance:
                        print(f"[Escape] 탈출 완료! 거리: {distance:.3f}m")
                        return True
                    break
        
        # ESC 키로 강제 종료
        if cv2.waitKey(1) & 0xFF == 27:  # ESC 키
            print("[Escape] 사용자가 탈출을 중단했습니다")
            break
    
    cv2.destroyAllWindows()
    return False
