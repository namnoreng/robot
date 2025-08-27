import cv2
import cv2.aruco as aruco
import numpy as np
import serial
import time
import platform

# 플랫폼 확인
current_platform = platform.system()

# 마커 크기 설정 - 실제 거리와 맞게 보정
marker_length = 0.029  # 보정된 마커 실제 길이(m)

# 화면 해상도 설정 정의
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

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

def center_align_driving(cap, aruco_dict, parameters, marker_index, serial_server, 
                        camera_matrix, dist_coeffs, target_distance=0.5, 
                        frame_width=CAMERA_WIDTH, frame_height=CAMERA_HEIGHT):
    """
    ArUco 마커가 화면 중앙에 오도록 평행이동하며 주행하는 함수
    
    Parameters:
    - cap: 카메라 객체
    - aruco_dict: ArUco 딕셔너리
    - parameters: ArUco 파라미터
    - marker_index: 추적할 마커 ID
    - serial_server: 시리얼 통신 객체
    - camera_matrix: 카메라 행렬
    - dist_coeffs: 왜곡 계수
    - target_distance: 목표 거리 (미터)
    - frame_width: 프레임 너비 (기본값: 640)
    - frame_height: 프레임 높이 (기본값: 480)
    """
    
    # 화면 중앙 좌표
    FRAME_CENTER_X = frame_width // 2
    FRAME_CENTER_Y = frame_height // 2
    
    # 허용 오차 설정 (픽셀 단위)
    CENTER_TOLERANCE_X = 30  # 좌우 중앙 허용 오차
    CENTER_TOLERANCE_Y = 40  # 상하 중앙 허용 오차
    DISTANCE_TOLERANCE = 0.05 # 거리 허용 오차 (미터)
    
    # 이동 속도 조절을 위한 변수
    movement_delay = 0.15    # 명령 간 딜레이 (초)
    fine_tune_delay = 0.1    # 미세 조정 딜레이 (초)
    
    # 마커 추적 상태 변수
    last_marker_position = None
    marker_lost_count = 0
    MAX_LOST_FRAMES = 15
    
    # 동작 상태 추적
    current_action = "searching"  # searching, centering, approaching, completed
    
    print(f"[Center-Align] 마커 {marker_index} 중앙 정렬 주행 시작")
    print(f"[Center-Align] 목표: 화면 중앙({FRAME_CENTER_X}, {FRAME_CENTER_Y}), 목표 거리: {target_distance}m")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Center-Align] 카메라 프레임 읽기 실패")
                break

            # ArUco 마커 검출 및 정보 추출
            result = find_aruco_info(
                frame, aruco_dict, parameters, marker_index, 
                camera_matrix, dist_coeffs, marker_length
            )
            distance, (x_angle, y_angle, z_angle), (center_x, center_y) = result

            # 시각화를 위한 프레임 표시 (선택사항)
            display_frame = frame.copy()
            
            # 화면 중앙 표시
            cv2.circle(display_frame, (FRAME_CENTER_X, FRAME_CENTER_Y), 10, (0, 255, 255), 2)
            cv2.line(display_frame, (FRAME_CENTER_X-30, FRAME_CENTER_Y), (FRAME_CENTER_X+30, FRAME_CENTER_Y), (0, 255, 255), 2)
            cv2.line(display_frame, (FRAME_CENTER_X, FRAME_CENTER_Y-30), (FRAME_CENTER_X, FRAME_CENTER_Y+30), (0, 255, 255), 2)

            if distance is not None:
                # 마커를 찾았을 때
                marker_lost_count = 0
                last_marker_position = (center_x, center_y)
                
                # 마커 중심 표시
                cv2.circle(display_frame, (center_x, center_y), 8, (0, 255, 0), -1)
                cv2.line(display_frame, (FRAME_CENTER_X, FRAME_CENTER_Y), (center_x, center_y), (255, 0, 0), 2)
                
                # 정보 표시 (각도 정보 제외)
                info_text = [
                    f"Marker {marker_index}: Distance {distance:.3f}m",
                    f"Position: ({center_x}, {center_y})",
                    f"Target: ({FRAME_CENTER_X}, {FRAME_CENTER_Y})"
                ]
                
                for i, text in enumerate(info_text):
                    cv2.putText(display_frame, text, (10, 30 + i*25), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 오차 계산
                dx = center_x - FRAME_CENTER_X  # 좌우 오차 (오른쪽이 +)
                dy = center_y - FRAME_CENTER_Y  # 상하 오차 (아래쪽이 +)
                distance_error = distance - target_distance
                
                print(f"[Center-Align] 거리: {distance:.3f}m (목표: {target_distance}m), "
                      f"위치 오차: ({dx:+4.0f}, {dy:+4.0f})")
                
                # 목표 거리 도달 확인 (즉시 정지)
                if abs(distance_error) <= DISTANCE_TOLERANCE:
                    print(f"[Center-Align] 목표 거리 도달! 거리: {distance:.3f}m, 위치: ({center_x}, {center_y})")
                    current_action = "completed"
                    if serial_server:
                        serial_server.write('9'.encode())  # 정지
                    break
                
                # 중앙 정렬 우선 처리 (거리와 상관없이)
                # 좌우 조정이 최우선
                if abs(dx) > CENTER_TOLERANCE_X:
                    current_action = "centering_horizontal"
                    if dx > 0:
                        print(f"[Center-Align] 오른쪽으로 평행이동 (오차: {dx:+4.0f}px, 거리: {distance:.3f}m)")
                        if serial_server:
                            serial_server.write('6'.encode())  # 오른쪽 이동
                    else:
                        print(f"[Center-Align] 왼쪽으로 평행이동 (오차: {dx:+4.0f}px, 거리: {distance:.3f}m)")
                        if serial_server:
                            serial_server.write('5'.encode())  # 왼쪽 이동
                    time.sleep(movement_delay)
                    
                # 좌우가 중앙에 맞춰지면 상하 조정
                elif abs(dy) > CENTER_TOLERANCE_Y:
                    current_action = "centering_vertical"
                    if dy > 0:
                        print(f"[Center-Align] 후진으로 위치 조정 (오차: {dy:+4.0f}px, 거리: {distance:.3f}m)")
                        if serial_server:
                            serial_server.write('2'.encode())  # 후진
                    else:
                        print(f"[Center-Align] 전진으로 위치 조정 (오차: {dy:+4.0f}px, 거리: {distance:.3f}m)")
                        if serial_server:
                            serial_server.write('1'.encode())  # 전진
                    time.sleep(movement_delay)
                    
                # 중앙 정렬이 완료되면 거리 조정 (목표 거리보다 멀 때만 접근)
                else:
                    if distance > target_distance:
                        current_action = "approaching"
                        print(f"[Center-Align] 중앙 정렬됨 - 목표 거리로 접근 중 (현재: {distance:.3f}m, 목표: {target_distance}m)")
                        if serial_server:
                            serial_server.write('1'.encode())  # 전진
                        time.sleep(movement_delay)
                    else:
                        # 목표 거리보다 가깝거나 같으면 정지
                        print(f"[Center-Align] 중앙 정렬 완료 및 적정 거리 유지! 거리: {distance:.3f}m, 위치: ({center_x}, {center_y})")
                        current_action = "completed"
                        if serial_server:
                            serial_server.write('9'.encode())  # 정지
                        break
                    
            else:
                # 마커를 찾지 못했을 때
                marker_lost_count += 1
                current_action = "searching"
                
                cv2.putText(display_frame, f"Searching Marker {marker_index}... ({marker_lost_count}/{MAX_LOST_FRAMES})", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                print(f"[Center-Align] 마커 {marker_index} 탐색 중... ({marker_lost_count}/{MAX_LOST_FRAMES})")
                
                if marker_lost_count >= MAX_LOST_FRAMES:
                    if last_marker_position is not None:
                        # 마지막 위치를 기반으로 탐색 동작
                        last_x, last_y = last_marker_position
                        print(f"[Center-Align] 마지막 위치 기반 탐색: ({last_x}, {last_y})")
                        
                        # 마지막 위치를 기준으로 적절한 방향으로 이동
                        if last_x < FRAME_CENTER_X - 100:  # 왼쪽에 있었음
                            print("[Center-Align] 마커가 왼쪽에 있었음 - 왼쪽으로 탐색")
                            if serial_server:
                                serial_server.write('5'.encode())
                        elif last_x > FRAME_CENTER_X + 100:  # 오른쪽에 있었음
                            print("[Center-Align] 마커가 오른쪽에 있었음 - 오른쪽으로 탐색")
                            if serial_server:
                                serial_server.write('6'.encode())
                        else:
                            # 중앙 근처에서 사라진 경우 - 후진해서 시야 확보
                            print("[Center-Align] 후진하여 시야 확보")
                            if serial_server:
                                serial_server.write('2'.encode())
                        
                        time.sleep(0.5)
                        if serial_server:
                            serial_server.write('9'.encode())  # 정지
                        marker_lost_count = 0
                    else:
                        print("[Center-Align] 마커를 찾을 수 없어 탐색을 중단합니다.")
                        break
                else:
                    # 잠시 정지하고 다시 탐색
                    if serial_server:
                        serial_server.write('9'.encode())
            
            # 화면 표시 (디버깅용 - 필요시 주석 해제)
            # cv2.imshow(f"Center Align Driving - Marker {marker_index}", display_frame)
            
            # ESC 키로 종료
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("[Center-Align] 사용자가 종료했습니다.")
                break
            elif key == ord('s'):  # 스크린샷
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"center_align_marker_{marker_index}_{timestamp}.jpg"
                cv2.imwrite(filename, display_frame)
                print(f"[Center-Align] 스크린샷 저장: {filename}")
            
            # 프레임 처리 딜레이
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("[Center-Align] 키보드 인터럽트로 종료합니다.")
    except Exception as e:
        print(f"[Center-Align] 오류 발생: {e}")
    finally:
        # 정리 작업
        if serial_server:
            serial_server.write('9'.encode())  # 정지
        cv2.destroyAllWindows()
        print(f"[Center-Align] 마커 {marker_index} 중앙 정렬 주행 종료")
        
    return current_action == "completed"

def multi_marker_center_align(cap, aruco_dict, parameters, marker_sequence, serial_server, 
                             camera_matrix, dist_coeffs, target_distances=None,
                             frame_width=640, frame_height=480):
    """
    여러 마커를 순서대로 중앙 정렬하며 주행하는 함수
    
    Parameters:
    - cap: 카메라 객체
    - aruco_dict: ArUco 딕셔너리
    - parameters: ArUco 파라미터
    - marker_sequence: 추적할 마커 ID 시퀀스 (리스트)
    - serial_server: 시리얼 통신 객체
    - camera_matrix: 카메라 행렬
    - dist_coeffs: 왜곡 계수
    - target_distances: 각 마커별 목표 거리 리스트 (None이면 모두 0.5m)
    - frame_width: 프레임 너비
    - frame_height: 프레임 높이
    """
    
    if target_distances is None:
        target_distances = [0.5] * len(marker_sequence)
    
    if len(target_distances) != len(marker_sequence):
        target_distances = [0.5] * len(marker_sequence)
    
    print(f"[Multi-Align] 다중 마커 중앙 정렬 주행 시작")
    print(f"[Multi-Align] 마커 시퀀스: {marker_sequence}")
    print(f"[Multi-Align] 목표 거리: {target_distances}")
    
    successful_markers = []
    
    for i, marker_id in enumerate(marker_sequence):
        target_dist = target_distances[i]
        print(f"\n[Multi-Align] {i+1}/{len(marker_sequence)} - 마커 {marker_id} 처리 시작 (목표 거리: {target_dist}m)")
        
        # 개별 마커 중앙 정렬 실행
        success = center_align_driving(
            cap, aruco_dict, parameters, marker_id, serial_server,
            camera_matrix, dist_coeffs, target_dist, frame_width, frame_height
        )
        
        if success:
            successful_markers.append(marker_id)
            print(f"[Multi-Align] 마커 {marker_id} 중앙 정렬 완료!")
            
            # 다음 마커로 이동하기 전 잠시 대기
            if i < len(marker_sequence) - 1:
                print(f"[Multi-Align] 다음 마커 {marker_sequence[i+1]}로 이동 준비...")
                time.sleep(1.0)
        else:
            print(f"[Multi-Align] 마커 {marker_id} 중앙 정렬 실패!")
            break
    
    print(f"\n[Multi-Align] 다중 마커 중앙 정렬 완료")
    print(f"[Multi-Align] 성공한 마커: {successful_markers}")
    print(f"[Multi-Align] 성공률: {len(successful_markers)}/{len(marker_sequence)}")
    
    return successful_markers

# 메인 테스트 함수
def main():
    """
    테스트용 메인 함수
    """
    print("=== ArUco 마커 중앙 정렬 주행 테스트 ===")
    
    # 카메라 초기화 (CSI 카메라 또는 USB 카메라)
    try:
        # CSI 카메라 시도 (Jetson Nano)
        if current_platform == "Linux":
            # GStreamer 파이프라인으로 CSI 카메라 초기화
            gst_pipeline = (
                "nvarguscamerasrc ! "
                "video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=30/1 ! "
                "nvvidconv ! "
                "video/x-raw, format=BGR ! "
                "appsink"
            )
            cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
            print("CSI 카메라 초기화 성공")
        else:
            # USB 카메라
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            print("USB 카메라 초기화 성공")
            
    except Exception as e:
        print(f"카메라 초기화 실패: {e}")
        return
    
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return
    
    # 카메라 보정 데이터 로드 (실제 파일 경로로 수정 필요)
    try:
        camera_matrix = np.load("camera_matrix.npy")
        dist_coeffs = np.load("dist_coeffs.npy")
        print("카메라 보정 데이터 로드 성공")
    except:
        # 기본값 사용 (실제 보정 데이터로 교체 권장)
        camera_matrix = np.array([[400, 0, 320], [0, 400, 240], [0, 0, 1]], dtype=np.float32)
        dist_coeffs = np.zeros((4, 1))
        print("기본 카메라 매트릭스 사용 (보정 권장)")
    
    # 시리얼 통신 초기화 (실제 포트로 수정 필요)
    serial_server = None
    try:
        if current_platform == "Linux":
            serial_server = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        else:
            serial_server = serial.Serial('COM3', 9600, timeout=1)
        print("시리얼 통신 초기화 성공")
    except:
        print("시리얼 통신 초기화 실패 - 데모 모드로 실행")
    
    try:
        print("\n테스트 옵션을 선택하세요:")
        print("1. 단일 마커 중앙 정렬 (마커 0)")
        print("2. 다중 마커 중앙 정렬 (마커 0 -> 1 -> 2)")
        print("3. 커스텀 마커 시퀀스")
        
        choice = input("선택 (1-3): ").strip()
        
        if choice == "1":
            # 단일 마커 테스트
            marker_id = 0
            target_dist = 0.5
            print(f"\n마커 {marker_id} 중앙 정렬 테스트 시작...")
            success = center_align_driving(
                cap, marker_dict, param_markers, marker_id, serial_server,
                camera_matrix, dist_coeffs, target_dist
            )
            print(f"결과: {'성공' if success else '실패'}")
            
        elif choice == "2":
            # 다중 마커 테스트
            marker_sequence = [0, 1, 2]
            target_distances = [0.6, 0.5, 0.4]
            print(f"\n다중 마커 중앙 정렬 테스트 시작...")
            successful_markers = multi_marker_center_align(
                cap, marker_dict, param_markers, marker_sequence, serial_server,
                camera_matrix, dist_coeffs, target_distances
            )
            print(f"결과: {len(successful_markers)}/{len(marker_sequence)} 마커 성공")
            
        elif choice == "3":
            # 커스텀 시퀀스
            try:
                marker_input = input("마커 ID들을 쉼표로 구분하여 입력 (예: 0,1,2): ").strip()
                marker_sequence = [int(x.strip()) for x in marker_input.split(',')]
                
                dist_input = input(f"목표 거리들을 쉼표로 구분하여 입력 (예: 0.5,0.4,0.6) 또는 엔터(기본값 0.5): ").strip()
                if dist_input:
                    target_distances = [float(x.strip()) for x in dist_input.split(',')]
                else:
                    target_distances = None
                
                print(f"\n커스텀 마커 시퀀스 테스트 시작...")
                successful_markers = multi_marker_center_align(
                    cap, marker_dict, param_markers, marker_sequence, serial_server,
                    camera_matrix, dist_coeffs, target_distances
                )
                print(f"결과: {len(successful_markers)}/{len(marker_sequence)} 마커 성공")
                
            except Exception as e:
                print(f"입력 오류: {e}")
        
        else:
            print("잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    finally:
        # 정리
        cap.release()
        if serial_server:
            serial_server.close()
        cv2.destroyAllWindows()
        print("테스트 종료")

if __name__ == "__main__":
    main()
