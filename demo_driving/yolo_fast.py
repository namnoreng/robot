import cv2
import subprocess
import time
import threading
import os
from queue import Queue

# 설정 - 극도로 최적화된 버전
DARKNET_PATH = "./darknet"
CONFIG_PATH = "cfg/yolov4-tiny-custom.cfg"
WEIGHTS_PATH = "backup/yolov4-tiny-custom_best.weights"
DATA_PATH = "data/obj.data"

# 단일 임시 파일 사용 (파일 생성 오버헤드 최소화)
TEMP_FILENAME = "temp_frame.jpg"

# darknet 프로세스를 백그라운드로 실행하기 위한 큐
frame_queue = Queue(maxsize=1)
result_queue = Queue(maxsize=1)

def darknet_worker():
    """극도로 최적화된 darknet 워커"""
    while True:
        try:
            frame_data = frame_queue.get(timeout=1)
            if frame_data is None:
                break
        except:
            continue
            
        frame, frame_id = frame_data
        
        # 더욱 작은 해상도로 리사이즈 (속도 최우선)
        tiny_frame = cv2.resize(frame, (320, 320))  # 더 작게 변경
        cv2.imwrite(TEMP_FILENAME, tiny_frame, [cv2.IMWRITE_JPEG_QUALITY, 40])  # 품질도 더 낮춤
        
        # darknet 실행 (최소한의 옵션)
        cmd = [DARKNET_PATH, "detector", "test", DATA_PATH, CONFIG_PATH, WEIGHTS_PATH, TEMP_FILENAME, "-dont_show"]
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)  # 타임아웃 제거
            inference_time = time.time() - start_time
            
            print(f"[빠른모드] 프레임 {frame_id} 추론: {inference_time:.2f}초")
            
            # 결과 이미지 로드 (있는 경우만)
            result_img = None
            if os.path.exists("predictions.jpg"):
                result_img = cv2.imread("predictions.jpg")
            
            # 이전 결과 제거
            while not result_queue.empty():
                try:
                    result_queue.get_nowait()
                except:
                    break
            
            # 새 결과 저장
            result_queue.put({
                'frame_id': frame_id,
                'result_img': result_img,
                'inference_time': inference_time,
                'output': result.stdout.decode() if result.stdout else ""
            })
            
        except Exception as e:
            print(f"[빠른모드] 오류: {e}")

# 카메라 설정 (해상도도 줄임)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 워커 스레드 시작
worker_thread = threading.Thread(target=darknet_worker, daemon=True)
worker_thread.start()

# 변수 초기화
fps_start_time = time.time()
fps_counter = 0
frame_id = 0
latest_result = None

print("극도 최적화 YOLO (ESC로 종료)")
print("품질보다 속도를 우선합니다!")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_id += 1
    
    # 15프레임마다만 추론 (더 빈도 줄임)
    if frame_id % 15 == 0 and frame_queue.empty():
        frame_queue.put((frame.copy(), frame_id))
    
    # 결과 업데이트
    while not result_queue.empty():
        latest_result = result_queue.get()
    
    # 화면 표시
    display_frame = frame.copy()
    if latest_result and latest_result['result_img'] is not None:
        result_resized = cv2.resize(latest_result['result_img'], 
                                  (display_frame.shape[1], display_frame.shape[0]))
        display_frame = result_resized
        
        cv2.putText(display_frame, f"Fast Mode: {latest_result['inference_time']:.1f}s", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Frame: {latest_result['frame_id']}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # FPS 표시
    fps_counter += 1
    if fps_counter % 30 == 0:
        fps_end_time = time.time()
        fps = 30 / (fps_end_time - fps_start_time)
        fps_start_time = fps_end_time
        print(f"Display FPS: {fps:.1f}")
    
    cv2.putText(display_frame, f"FPS: {fps_counter/(time.time()-fps_start_time+0.001):.1f}", 
                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow("YOLO Fast Mode", display_frame)
    
    if cv2.waitKey(1) & 0xFF == 27:
        break

# 정리
frame_queue.put(None)
cap.release()
cv2.destroyAllWindows()

# 임시 파일 정리
try:
    os.remove(TEMP_FILENAME)
    os.remove("predictions.jpg")
except:
    pass

print("고속 모드 종료")
