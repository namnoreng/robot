import cv2
import numpy as np
import time

# YOLO 설정
CONFIG_PATH = "cfg/yolov4-tiny-custom.cfg"
WEIGHTS_PATH = "backup/yolov4-tiny-custom_best.weights"
CLASSES_FILE = "data/obj.names"  # 클래스 이름 파일

# 클래스 이름 로드 (obj.names 파일이 있다면)
try:
    with open(CLASSES_FILE, 'r') as f:
        classes = [line.strip() for line in f.readlines()]
except:
    classes = ["wheel"]  # 기본값으로 바퀴 설정

# YOLO 네트워크 로드
print("YOLO 모델 로딩 중...")
net = cv2.dnn.readNet(WEIGHTS_PATH, CONFIG_PATH)

# Jetson Nano GPU 사용 설정 (CUDA 백엔드)
try:
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    print("CUDA 백엔드 사용")
except:
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    print("CPU 백엔드 사용")

# 출력 레이어 이름 가져오기
layer_names = net.getLayerNames()
output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

# 카메라 열기 및 해상도 세팅
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# FPS 계산용
fps_start_time = time.time()
fps_counter = 0

print("실시간 YOLO 객체 탐지 시작 (ESC 키로 종료)")

while True:
    ret, frame = cap.read()
    if not ret:
        print("카메라 프레임 캡처 실패!")
        break
    
    height, width, channels = frame.shape
    
    # YOLO 입력을 위한 blob 생성
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    
    # 추론 실행
    start_time = time.time()
    outputs = net.forward(output_layers)
    inference_time = time.time() - start_time
    
    # 결과 처리
    boxes = []
    confidences = []
    class_ids = []
    
    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            if confidence > 0.5:  # 신뢰도 임계값
                # 바운딩 박스 좌표 계산
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)
    
    # Non-Maximum Suppression 적용
    indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    
    # 결과 그리기
    if len(indices) > 0:
        for i in indices.flatten():
            x, y, w, h = boxes[i]
            confidence = confidences[i]
            class_id = class_ids[i]
            
            label = f"{classes[class_id] if class_id < len(classes) else 'Unknown'}: {confidence:.2f}"
            color = (0, 255, 0)  # 초록색
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # FPS 계산 및 표시
    fps_counter += 1
    if fps_counter % 10 == 0:  # 10프레임마다 FPS 계산
        fps_end_time = time.time()
        fps = 10 / (fps_end_time - fps_start_time)
        fps_start_time = fps_end_time
        print(f"FPS: {fps:.2f}, 추론 시간: {inference_time*1000:.2f}ms")
    
    # FPS 정보를 화면에 표시
    cv2.putText(frame, f"Inference: {inference_time*1000:.1f}ms", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow("YOLO Real-time Detection", frame)
    
    # ESC 키로 종료
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC 키
        break

cap.release()
cv2.destroyAllWindows()
print("프로그램 종료")
