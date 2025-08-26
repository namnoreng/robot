# 카메라 테스트 도구 모음

이 폴더에는 Jetson Nano 카메라 성능 분석 및 Rolling Shutter 문제 해결을 위한 테스트 도구들이 들어있습니다.

## 📁 파일 목록

### 🔧 **rolling_shutter_test.py**
- **용도**: Rolling Shutter 현상 테스트 및 최적화
- **기능**: 
  - ArUco 마커 검출과 함께 rolling shutter 최적화
  - 다양한 카메라 설정 테스트 (노출, 게인, 밝기)
  - 순수 카메라 성능 테스트 (ArUco 없음)
- **실행**: `python3 rolling_shutter_test.py`

### 🔍 **camera_debug.py**
- **용도**: 카메라 하드웨어 기본 진단
- **기능**:
  - 카메라 하드웨어 정보 수집
  - 백엔드별 성능 비교 (V4L2, GStreamer, FFmpeg)
  - USB 장치 분석
  - 원시 캡처 성능 측정
- **실행**: `python3 camera_debug.py`

### ⚡ **camera_optimization.py**
- **용도**: 해상도별 성능 최적화 테스트
- **기능**:
  - 다양한 해상도에서 FPS 측정
  - GStreamer 파이프라인 직접 테스트
  - MJPEG 압축 성능 테스트
- **실행**: `python3 camera_optimization.py`

### 🏥 **advanced_camera_test.py**
- **용도**: 고급 카메라 진단 및 문제 해결
- **기능**:
  - V4L2 명령어로 강제 해상도 설정
  - 다양한 픽셀 형식 테스트 (YUYV, MJPG, YUY2, UYVY)
  - USB 전원 상태 확인
- **실행**: `python3 advanced_camera_test.py`

### 🚀 **csi_aruco_final.py** ⭐ **NEW!**
- **용도**: CSI 카메라를 이용한 완전한 ArUco 마커 인식
- **기능**:
  - Jetson Nano CSI 카메라 지원
  - 실시간 거리 측정 (pose estimation)
  - 마커 각도 및 위치 정보
  - 카메라 보정 파일 자동 로딩
  - 기존 프로젝트와 호환되는 구조
- **실행**: `python3 csi_aruco_final.py`
- **특징**: USB 카메라보다 훨씬 좋은 성능!

### 📋 **camera_info.sh**
- **용도**: 시스템 레벨 카메라 정보 수집
- **기능**:
  - v4l2-utils 자동 설치
  - 카메라 장치 목록 및 지원 형식 조회
  - USB 장치 정보 및 시스템 로그 확인
- **실행**: `chmod +x camera_info.sh && ./camera_info.sh`

## 🚀 사용 순서 (권장)

### **USB 카메라 사용 시:**

#### 1단계: 기본 진단
```bash
./camera_info.sh  # 시스템 정보 수집
python3 camera_debug.py  # 옵션 5 (전체 실행)
```

#### 2단계: 성능 최적화
```bash
python3 optimal_camera_test.py  # v4l2-ctl 결과 기반 최적화
```

#### 3단계: Rolling Shutter 해결
```bash
python3 rolling_shutter_test.py  # 옵션 1 또는 2
```

### **CSI 카메라 사용 시 (권장!):**

#### 단일 단계: 직접 ArUco 검출
```bash
python3 csi_aruco_final.py  # CSI 카메라로 바로 ArUco 검출
```

**CSI 카메라 장점:**
- USB 대역폭 제한 없음
- 30fps 안정적 달성
- Rolling Shutter 문제 최소화
- 하드웨어 가속 지원

## 🔧 주요 발견사항

### **USB 카메라 한계:**
- **현재 문제**: 카메라가 2304x1536@2fps로 고정됨
- **해상도 설정**: OpenCV로는 해상도 변경 불가능
- **최고 성능**: GStreamer 백엔드에서 5.4fps
- **권장 해결책**: MJPG 압축 + 소프트웨어 리사이징

### **CSI 카메라 해결책:**
- **30fps 안정적 달성** ✅
- **Rolling Shutter 최소화** ✅
- **실시간 거리 측정** ✅
- **하드웨어 가속 지원** ✅

## 💡 팁

### **USB 카메라:**
- Jetson Nano에서는 GStreamer 백엔드가 가장 좋은 성능
- v4l2-utils로 `v4l2-ctl --list-formats-ext` 실행하여 지원 해상도 확인
- MJPG 압축 사용으로 대역폭 절약
- USB 전력 부족 시 별도 전원 공급 USB 허브 사용

### **CSI 카메라 (권장!):**
- `nvarguscamerasrc` 사용으로 하드웨어 가속
- 1280x720 → 640x480 다운스케일링으로 성능 최적화
- 카메라 보정 파일 (`camera_matrix.npy`, `dist_coeffs.npy`) 필요시 자동 로딩
- ArUco 마커 크기는 실제 물리적 크기로 설정 (기본: 5cm)
