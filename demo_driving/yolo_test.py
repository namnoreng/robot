import cv2
import subprocess
import time
import threading
import os
from queue import Queue

# 설정
DARKNET_PATH = "./darknet"
CONFIG_PATH = "cfg/yolov4-tiny-custom.cfg"
WEIGHTS_PATH = "backup/yolov4-tiny-custom_best.weights"
DATA_PATH = "data/obj.data"

# darknet 프로세스를 백그라운드로 실행하기 위한 큐
frame_queue = Queue(maxsize=1)  # 큐 크기를 1로 줄임
result_queue = Queue(maxsize=1)  # 결과 큐도 최대 1개로 제한

def darknet_worker():
    """백그라운드에서 darknet을 실행하는 워커"""
    while True:
        try:
            frame_data = frame_queue.get(timeout=1)  # 1초 타임아웃
            if frame_data is None:  # 종료 신호
                break
        except:
            continue  # 타임아웃 시 계속 진행
            
        frame, frame_id = frame_data
        
        # 프레임을 훨씬 더 작은 크기로 리사이즈 (속도 우선)
        small_frame = cv2.resize(frame, (320, 240))  # 더 작은 해상도로 변경
        temp_filename = f"temp_frame_{frame_id}.jpg"
        cv2.imwrite(temp_filename, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])  # 품질 더 낮춤
        
        # darknet 실행
        cmd = [
            DARKNET_PATH, "detector", "test",
            DATA_PATH, CONFIG_PATH, WEIGHTS_PATH,
            temp_filename,
            "-dont_show", "-ext_output"
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)  # 타임아웃 3초로 단축
            inference_time = time.time() - start_time
            
            print(f"[정보] 프레임 {frame_id} 추론 완료: {inference_time:.2f}초")  # 추론 시간 로그
            
            # 결과 이미지 로드
            result_img = None
            if os.path.exists("predictions.jpg"):
                result_img = cv2.imread("predictions.jpg")
            
            # 결과 큐가 가득 찬 경우 기존 결과 제거
            while not result_queue.empty():
                try:
                    result_queue.get_nowait()
                except:
                    break
            
            # 결과를 큐에 저장
            result_queue.put({
                'frame_id': frame_id,
                'result_img': result_img,
                'inference_time': inference_time,
                'output': result.stdout.decode() if result.stdout else ""
            })
            
        except subprocess.TimeoutExpired:
            print(f"[경고] 프레임 {frame_id} 추론 시간 초과 (3초) - 건너뜀")
        except Exception as e:
            print(f"[오류] 프레임 {frame_id} 처리 실패: {e}")
        
        # 임시 파일 삭제
        try:
            os.remove(temp_filename)
        except:
            pass# 카메라 열기 및 해상도 세팅
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# darknet 워커 스레드 시작
worker_thread = threading.Thread(target=darknet_worker, daemon=True)
worker_thread.start()

# FPS 계산용
fps_start_time = time.time()
fps_counter = 0
frame_id = 0
latest_result = None

print("최적화된 YOLO 객체 탐지 시작 (ESC 키로 종료)")
print("처음 몇 프레임은 느릴 수 있습니다...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("카메라 프레임 캡처 실패!")
        break
    
    frame_id += 1
    
    # 프레임을 큐에 추가 (10프레임마다만 추론에 보냄)
    if frame_id % 10 == 0 and frame_queue.empty():  # 10프레임마다로 더 줄임
        frame_queue.put((frame.copy(), frame_id))
    
    # 결과가 있으면 가져오기 (최신 결과만 사용)
    while not result_queue.empty():
        latest_result = result_queue.get()
    
    # 최신 결과 표시
    display_frame = frame.copy()
    if latest_result and latest_result['result_img'] is not None:
        # 원본 프레임 크기로 결과 이미지 리사이즈
        result_resized = cv2.resize(latest_result['result_img'], 
                                  (display_frame.shape[1], display_frame.shape[0]))
        display_frame = result_resized
        
        # 추론 시간 표시
        cv2.putText(display_frame, 
                   f"Inference: {latest_result['inference_time']*1000:.1f}ms", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 프레임 ID 표시
        cv2.putText(display_frame, 
                   f"Frame ID: {latest_result['frame_id']}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # FPS 계산 및 표시
    fps_counter += 1
    if fps_counter % 30 == 0:  # 30프레임마다 FPS 계산
        fps_end_time = time.time()
        fps = 30 / (fps_end_time - fps_start_time)
        fps_start_time = fps_end_time
        print(f"Display FPS: {fps:.2f}")
    
    # 현재 FPS 화면에 표시
    cv2.putText(display_frame, f"Display FPS: {fps_counter/(time.time()-fps_start_time+0.001):.1f}", 
                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow("YOLO Optimized Detection", display_frame)
    
    # ESC 키로 종료
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC 키
        break

# 정리
frame_queue.put(None)  # 워커 스레드 종료 신호
cap.release()
cv2.destroyAllWindows()
print("프로그램 종료")
