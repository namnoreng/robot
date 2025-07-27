import cv2
import cv2.aruco as aruco
import numpy as np
import serial
import time

# 마커 크기 설정
marker_length = 0.05

cv_version = cv2.__version__.split(".")
if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
    print("Using OpenCV 3.x")
else:
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters()
    print("Using OpenCV 4.x")

def flush_camera(cap, num=5):
    for _ in range(num):
        cap.read()

def initialize_robot(cap, aruco_dict, parameters, marker_index, serial_server, camera_matrix, dist_coeffs):
    FRAME_CENTER_X = 640   # 1280x720 해상도 기준
    FRAME_CENTER_Y = 360
    CENTER_TOLERANCE = 30  # 중앙 허용 오차 (픽셀)
    ANGLE_TOLERANCE = 5    # 각도 허용 오차 (도)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("카메라 프레임을 읽지 못했습니다.")
            continue

        result = find_aruco_info(
            frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length
        )
        print("find_aruco_info result:", result)
        distance, (x_angle, y_angle, z_angle), (center_x, center_y) = result

        if distance is not None:
            dx = center_x - FRAME_CENTER_X
            angle_error = z_angle

            print(f"중심 오차: ({dx}), 각도 오차: {angle_error:.2f}")

            # 1. 회전값 먼저 맞추기
            if abs(angle_error) > ANGLE_TOLERANCE:
                if angle_error > 0:
                    print("좌회전")
                    serial_server.write('3'.encode())
                else:
                    print("우회전")
                    serial_server.write('4'.encode())
                continue  # 회전이 맞을 때까지 중앙값 동작으로 넘어가지 않음

            # 2. 회전이 맞으면 중앙값 맞추기
            if abs(dx) > CENTER_TOLERANCE:
                if dx > 0:
                    print("오른쪽으로 이동")
                    serial_server.write('6'.encode())
                else:
                    print("왼쪽으로 이동")
                    serial_server.write('5'.encode())
                continue  # 중앙이 맞을 때까지 반복

            # 3. 둘 다 맞으면 정지
            print("초기화 완료: 중앙+수직")
            serial_server.write('9'.encode())  # 정지 명령
            break

        else:
            print("마커를 찾지 못했습니다.")
            serial_server.write('9'.encode())  # 마커를 찾지 못했을 때 정지 명령

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
            print(f"ID: {marker_index} Rotation (X, Y, Z): ({x_angle:.2f}, {y_angle:.2f}, {z_angle:.2f})")
            print(f"ID: {marker_index} Distance: {distance:.3f} m, Center: ({center_x}, {center_y})")

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
    frame: 입력 이미지 (BGR)
    aruco_dict, parameters: 아르코 딕셔너리 및 파라미터
    marker_index: 찾고자 하는 마커 ID
    camera_matrix, dist_coeffs: 카메라 보정값
    marker_length: 마커 실제 길이(m)
    반환값: (distance, (x_angle, y_angle, z_angle), (center_x, center_y)) 또는 (None, (None, None, None), (None, None))
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        for i in range(len(ids)):
            if ids[i][0] == marker_index:
                # 포즈 추정 (corners[i] → [corners[i]])
                cv_version = cv2.__version__.split(".")
                if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
                    # OpenCV 3.2.x 이하
                    rvecs, tvecs = aruco.estimatePoseSingleMarkers(
                        np.array([corners[i]]), marker_length, camera_matrix, dist_coeffs
                    )
                else:
                    # OpenCV 3.3.x 이상 또는 4.x
                    rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
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
    # 못 찾으면 None 반환
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
                        print(f"[Driving] 후방 마커{back_marker_id} 감지: {back_distance:.3f}m")
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
                        marker_centers = []
                        for i, marker_id in enumerate(ids):
                            if marker_id[0] == front_marker_id:  # 지정된 마커만 처리
                                # 마커 중심 계산
                                c = corners[i].reshape(4, 2)
                                center_x = int(np.mean(c[:, 0]))
                                marker_centers.append(center_x)
                        
                        if marker_centers:
                            # 여러 마커가 있으면 평균 중심 계산
                            avg_center_x = np.mean(marker_centers)
                            dx = avg_center_x - FRAME_CENTER_X
                            
                            print(f"[Driving] 전방 마커{front_marker_id} 개수: {len(marker_centers)}, 평균중심: {avg_center_x:.1f}, 오차: {dx:.1f}")
                            
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
