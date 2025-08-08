import cv2 as cv
import platform
import time
import numpy as np
import cv2.aruco as aruco

current_platform = platform.system()
test_marker_length = 0.05 # 마커의 크기를 5cm로 생각하고 거리 측정


def find_aruco_info(frame, aruco_dict, parameters, marker_index, camera_matrix, dist_coeffs, marker_length):
    """
    frame: 입력 이미지 (BGR)
    aruco_dict, parameters: 아르코 딕셔너리 및 파라미터
    marker_index: 찾고자 하는 마커 ID
    camera_matrix, dist_coeffs: 카메라 보정값
    marker_length: 마커 실제 길이(m)
    반환값: (distance, (x_angle, y_angle, z_angle), (center_x, center_y)) 또는 (None, (None, None, None), (None, None))
    """
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    corners, ids, _ = cv.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        for i in range(len(ids)):
            if ids[i][0] == marker_index:
                # 포즈 추정 (corners[i] → [corners[i]])
                cv_version = cv.__version__.split(".")
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
                rotation_matrix, _ = cv.Rodrigues(rvecs[0][0])
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

def configure_camera_manual_settings(cap, camera_name="Camera", exposure=-7, wb_temp=4000, brightness=128, contrast=128, saturation=128, gain=0):
    """
    카메라의 자동 기능을 비활성화하고 수동 설정을 적용하는 함수
    
    Parameters:
    - cap: cv2.VideoCapture 객체
    - camera_name: 카메라 이름 (로그용)
    - exposure: 노출 값 (-13 ~ -1, 낮을수록 어두움)
    - wb_temp: 화이트 밸런스 온도 (2800~6500K)
    - brightness: 밝기 (0~255)
    - contrast: 대비 (0~255)
    - saturation: 채도 (0~255)
    - gain: 게인 (0~255, 낮을수록 노이즈 적음)
    """
    print(f"=== {camera_name} 수동 설정 적용 ===")
    
    # 자동 기능 비활성화
    cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 자동 노출 비활성화 (수동 모드)
    cap.set(cv.CAP_PROP_AUTO_WB, 0)           # 자동 화이트 밸런스 비활성화
    
    # 수동 값 설정
    cap.set(cv.CAP_PROP_EXPOSURE, exposure)
    cap.set(cv.CAP_PROP_WB_TEMPERATURE, wb_temp)
    cap.set(cv.CAP_PROP_BRIGHTNESS, brightness)
    cap.set(cv.CAP_PROP_CONTRAST, contrast)
    cap.set(cv.CAP_PROP_SATURATION, saturation)
    cap.set(cv.CAP_PROP_GAIN, gain)
    
    # 설정 확인
    print(f"자동노출: {cap.get(cv.CAP_PROP_AUTO_EXPOSURE)} (0.25=수동)")
    print(f"노출값: {cap.get(cv.CAP_PROP_EXPOSURE)}")
    print(f"자동WB: {cap.get(cv.CAP_PROP_AUTO_WB)} (0=비활성화)")
    print(f"WB온도: {cap.get(cv.CAP_PROP_WB_TEMPERATURE)}K")
    print(f"밝기: {cap.get(cv.CAP_PROP_BRIGHTNESS)}")
    print(f"대비: {cap.get(cv.CAP_PROP_CONTRAST)}")
    print(f"채도: {cap.get(cv.CAP_PROP_SATURATION)}")
    print(f"게인: {cap.get(cv.CAP_PROP_GAIN)}")
    print("=" * (len(camera_name) + 16))

# 카메라 초기화 (윈도우/리눅스 분기) - 안정성 강화
print("=== 카메라 초기화 시작 ===")

# 먼저 사용 가능한 카메라 인덱스 확인
available_cameras = []
for i in range(5):  # 0~4번 카메라 테스트
    test_cap = cv.VideoCapture(i)
    if test_cap.isOpened():
        available_cameras.append(i)
        test_cap.release()
    time.sleep(0.1)  # 짧은 대기

print(f"사용 가능한 카메라: {available_cameras}")

if not available_cameras:
    print("❌ 사용 가능한 카메라가 없습니다.")
    exit(1)

# 첫 번째 사용 가능한 카메라 사용
camera_index = available_cameras[0]
print(f"카메라 인덱스 {camera_index} 사용")

if current_platform == "Windows":
    cap_front = cv.VideoCapture(camera_index, cv.CAP_DSHOW)
else:
    # Jetson Nano에서 V4L2 백엔드 사용
    cap_front = cv.VideoCapture(0,cv.CAP_V4L2)

# 초기 설정 전에 카메라 연결 확인
if not cap_front.isOpened():
    print("❌ 카메라 초기 연결 실패")
    exit(1)

# 기본 해상도로 먼저 설정 (안정성 우선)
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 640)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
cap_front.set(cv.CAP_PROP_FPS, 30)

# 몇 개 프레임을 읽어서 카메라 안정화
print("카메라 안정화 중...")
for i in range(10):
    ret, frame = cap_front.read()
    if ret:
        print(f"프레임 {i+1}/10 읽기 성공")
    else:
        print(f"프레임 {i+1}/10 읽기 실패")
    time.sleep(0.1)

# 이제 원하는 해상도로 설정
print("목표 해상도 설정...")
cap_front.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
cap_front.set(cv.CAP_PROP_FRAME_HEIGHT, 720)

# 잔상 최소화를 위한 추가 설정
cap_front.set(cv.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기 최소화로 지연 감소

# 프레임 동기화 및 rolling shutter 문제 해결
try:
    cap_front.set(cv.CAP_PROP_AUTOFOCUS, 0)  # 오토포커스 비활성화
    cap_front.set(cv.CAP_PROP_FOCUS, 0)      # 포커스 고정
    
    # Rolling shutter 효과 최소화를 위한 설정
    cap_front.set(cv.CAP_PROP_EXPOSURE, -6)   # 노출 시간을 짧게 (rolling shutter 효과 감소)
    
    # 추가 동기화 설정
    cap_front.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # MJPEG 코덱 사용
except Exception as e:
    print(f"카메라 고급 설정 실패: {e}")

# 전방 카메라 수동 설정 적용 (잔상 최소화 및 적절한 밝기 조정)
try:
    configure_camera_manual_settings(cap_front, "전방 카메라", exposure=-6, wb_temp=4000, brightness=120, contrast=130, saturation=128, gain=20)
except Exception as e:
    print(f"카메라 수동 설정 실패: {e}")

# 설정 후 카메라 상태 재확인
if cap_front.isOpened():
    print("✅ front camera is opened and configured")
    # 테스트 프레임 읽기
    ret, test_frame = cap_front.read()
    if ret:
        print(f"✅ 테스트 프레임 읽기 성공 - 크기: {test_frame.shape}")
    else:
        print("❌ 테스트 프레임 읽기 실패")
else:
    print("❌ front camera 열기 실패 - 프로그램 종료")
    exit(1)

# npy 파일 불러오기
camera_front_matrix = np.load(r"camera_value/camera_front_matrix.npy")
dist_front_coeffs = np.load(r"camera_value/dist_front_coeffs.npy")

# 보정 행렬과 왜곡 계수를 불러옵니다.
print("Loaded front camera matrix : \n", camera_front_matrix)
print("Loaded front distortion coefficients : \n", dist_front_coeffs)

# OpenCV 버전에 따라 ArUco 파라미터 생성 방식 분기
cv_version = cv.__version__.split(".")
if int(cv_version[0]) == 3 and int(cv_version[1]) <= 2:
    marker_dict = aruco.Dictionary_get(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters_create()
else:
    marker_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
    param_markers = aruco.DetectorParameters()
    
    # ArUco 검출 파라미터 조정 (검출 성능 향상)
    param_markers.adaptiveThreshWinSizeMin = 3
    param_markers.adaptiveThreshWinSizeMax = 23
    param_markers.adaptiveThreshWinSizeStep = 10
    param_markers.adaptiveThreshConstant = 7
    param_markers.minMarkerPerimeterRate = 0.03
    param_markers.maxMarkerPerimeterRate = 4.0
    param_markers.polygonalApproxAccuracyRate = 0.03
    param_markers.minCornerDistanceRate = 0.05

# front 카메라만 사용
cap = cap_front
camera_matrix = camera_front_matrix
dist_coeffs = dist_front_coeffs

# 마커 실제 길이 조정 (실제 마커 크기에 맞게 수정 필요)
# 현재 0.17m로 측정되는데 실제는 0.10m이므로 비율 계산: 0.05 * (0.10/0.17) ≈ 0.029
MARKER_LENGTH = 0.029  # 마커 실제 길이(m) - 조정된 값

# 잔상 최소화를 위한 변수들
prev_frame = None
frame_count = 0
sync_buffer = []  # 프레임 동기화를 위한 버퍼

# 메인 루프 - 안정성 강화
print("=== 메인 루프 시작 ===")
frame_read_errors = 0
max_errors = 10

while True:
    ret, frame = cap.read()
    if not ret:
        frame_read_errors += 1
        print(f"프레임 읽기 실패 {frame_read_errors}/{max_errors}")
        
        if frame_read_errors >= max_errors:
            print("❌ 연속된 프레임 읽기 실패로 종료")
            break
            
        # 짧은 대기 후 재시도
        time.sleep(0.1)
        continue
    
    # 프레임 읽기 성공 시 에러 카운터 리셋
    frame_read_errors = 0
    
    # 프레임 유효성 검사
    if frame is None or frame.size == 0:
        print("빈 프레임 감지, 스킵")
        continue

    frame_count += 1
    
    # 프레임 동기화 개선 - 버퍼 완전 클리어 (주기 늘림)
    if frame_count % 30 == 0:  # 30프레임마다 동기화 (부하 감소)
        try:
            for _ in range(3):  # 제한된 버퍼 클리어
                if not cap.grab():
                    break
            ret, frame = cap.read()  # 새로운 프레임 읽기
            if not ret:
                continue
        except Exception as e:
            print(f"버퍼 클리어 중 오류: {e}")
            continue
    
    # 프레임 안정성 확인 (동일한 프레임 연속 체크 방지)
    if prev_frame is not None:
        try:
            diff = cv.absdiff(cv.cvtColor(frame, cv.COLOR_BGR2GRAY), 
                             cv.cvtColor(prev_frame, cv.COLOR_BGR2GRAY))
            if np.mean(diff) < 1:  # 프레임이 거의 동일하면 스킵
                continue
        except Exception as e:
            print(f"프레임 비교 중 오류: {e}")
    
    prev_frame = frame.copy()

    try:
        # 마커 검출 및 거리 계산
        # 단순한 전처리 (프레임 동기화에 집중)
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        
        # 가벼운 노이즈 제거만 적용
        blurred = cv.GaussianBlur(gray, (3, 3), 0)
        
        # 마커 검출
        corners, ids, _ = aruco.detectMarkers(blurred, marker_dict, parameters=param_markers)
        distance_text = "No marker detected"

        if ids is not None:
            rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(corners, MARKER_LENGTH, camera_matrix, dist_coeffs)
            # 마커 정보는 display_frame에서 처리됨
        else:
            distance_text = "No marker detected"

        # 화면 출력용 프레임 준비
        display_frame = frame.copy()  # 원본 프레임 사용
        
        # 마커 검출 결과를 display_frame에 그리기
        if ids is not None:
            aruco.drawDetectedMarkers(display_frame, corners, ids)
            for i, marker_id in enumerate(ids.flatten()):
                # 텍스트 정보 추가
                distance = tvecs[i][0][2]
                marker_pixel_size = np.linalg.norm(corners[i][0][0] - corners[i][0][2])
                
                distance_text = f"ID:{marker_id} Dist:{distance:.3f}m"
                size_text = f"Marker size: {MARKER_LENGTH*100:.1f}cm"
                pixel_text = f"Pixel size: {marker_pixel_size:.1f}px"
                
                # 축 그리기
                try:
                    cv.drawFrameAxes(display_frame, camera_matrix, dist_coeffs, rvecs[i], tvecs[i], 0.03)
                except AttributeError:
                    try:
                        aruco.drawAxis(display_frame, camera_matrix, dist_coeffs, rvecs[i], tvecs[i], 0.03)
                    except AttributeError:
                        pass
                
                cv.putText(display_frame, distance_text, (10, 40), cv.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                cv.putText(display_frame, size_text, (10, 80), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
                cv.putText(display_frame, pixel_text, (10, 110), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
                break
        else:
            cv.putText(display_frame, "No marker detected", (10, 40), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

        # 프레임 상태 표시
        status_text = f"Frame: {frame_count}"
        cv.putText(display_frame, status_text, (10, display_frame.shape[0]-20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

        cv.imshow("ArUco Distance Test", display_frame)
        
    except Exception as e:
        print(f"프레임 처리 중 오류: {e}")
        continue
    
    # 키 입력 처리 (더 빠른 반응을 위해 waitKey 시간 단축)
    key = cv.waitKey(1) & 0xFF
    if key == 27:  # ESC 키
        print("ESC 키로 종료")
        break
    elif key == ord('r'):  # 'r' 키로 카메라 버퍼 리셋
        try:
            for _ in range(5):
                cap.grab()
            print("카메라 버퍼 리셋 완료")
        except Exception as e:
            print(f"버퍼 리셋 실패: {e}")
    elif key == ord('q'):  # 'q' 키로도 종료 가능
        print("Q 키로 종료")
        break

print("=== 정리 중 ===")
cap.release()
cv.destroyAllWindows()
print("프로그램 종료 완료")