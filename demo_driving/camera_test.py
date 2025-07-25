import cv2 as cv
import time

print("=== Jetson Nano 카메라 테스트 ===")

# 연결된 카메라 확인
def test_camera(index):
    print(f"\n카메라 {index} 테스트 중...")
    
    # 기본 V4L2 백엔드로 시도
    cap = cv.VideoCapture(index, cv.CAP_V4L2)
    
    if cap.isOpened():
        print(f"✅ 카메라 {index}: V4L2로 성공 열림")
        ret, frame = cap.read()
        if ret:
            print(f"   해상도: {frame.shape[1]}x{frame.shape[0]}")
        else:
            print("   프레임 읽기 실패")
        cap.release()
        return True
    else:
        print(f"❌ 카메라 {index}: V4L2로 열기 실패")
        
        # 기본 백엔드로 재시도
        cap = cv.VideoCapture(index)
        if cap.isOpened():
            print(f"✅ 카메라 {index}: 기본 백엔드로 성공 열림")
            ret, frame = cap.read()
            if ret:
                print(f"   해상도: {frame.shape[1]}x{frame.shape[0]}")
            else:
                print("   프레임 읽기 실패")
            cap.release()
            return True
        else:
            print(f"❌ 카메라 {index}: 모든 백엔드로 열기 실패")
            cap.release()
            return False

# 카메라 0-3번까지 테스트
available_cameras = []
for i in range(4):
    if test_camera(i):
        available_cameras.append(i)

print(f"\n=== 결과 ===")
print(f"사용 가능한 카메라: {available_cameras}")

# 사용 가능한 카메라로 간단한 테스트
if len(available_cameras) >= 1:
    print(f"\n카메라 {available_cameras[0]}로 5초간 실시간 테스트...")
    cap = cv.VideoCapture(available_cameras[0], cv.CAP_V4L2)
    
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < 5:  # 5초간
        ret, frame = cap.read()
        if ret:
            frame_count += 1
            cv.imshow("Camera Test", frame)
            if cv.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("프레임 읽기 실패")
            break
    
    cap.release()
    cv.destroyAllWindows()
    
    fps = frame_count / 5
    print(f"FPS: {fps:.1f}")
else:
    print("사용 가능한 카메라가 없습니다!")

print("\n=== 추가 정보 ===")
print("만약 카메라가 인식되지 않으면:")
print("1. 'ls /dev/video*' 명령으로 비디오 장치 확인")
print("2. 'v4l2-ctl --list-devices' 명령으로 상세 정보 확인")
print("3. USB 카메라라면 다른 포트에 연결 시도")
