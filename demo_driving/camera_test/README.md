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

### 📋 **camera_info.sh**
- **용도**: 시스템 레벨 카메라 정보 수집
- **기능**:
  - v4l2-utils 자동 설치
  - 카메라 장치 목록 및 지원 형식 조회
  - USB 장치 정보 및 시스템 로그 확인
- **실행**: `chmod +x camera_info.sh && ./camera_info.sh`

## 🚀 사용 순서 (권장)

### 1단계: 기본 진단
```bash
./camera_info.sh  # 시스템 정보 수집
python3 camera_debug.py  # 옵션 5 (전체 실행)
```

### 2단계: 성능 최적화
```bash
python3 camera_optimization.py  # 옵션 4 (전체 테스트)
```

### 3단계: 고급 진단 (문제가 지속될 경우)
```bash
python3 advanced_camera_test.py  # 옵션 4 (전체 실행)
```

### 4단계: Rolling Shutter 해결
```bash
python3 rolling_shutter_test.py  # 옵션 1 (순수 카메라 테스트) 또는 옵션 2 (RS 테스트)
```

## 🔧 주요 발견사항

- **현재 문제**: 카메라가 2304x1536@2fps로 고정됨
- **해상도 설정**: OpenCV로는 해상도 변경 불가능
- **최고 성능**: GStreamer 백엔드에서 5.4fps
- **권장 해결책**: 소프트웨어 리사이징 또는 하드웨어 교체

## 💡 팁

- Jetson Nano에서는 GStreamer 백엔드가 가장 좋은 성능을 보임
- v4l2-utils 설치 후 `v4l2-ctl --list-formats-ext`로 실제 지원 해상도 확인 필수
- USB 전력 부족 시 별도 전원 공급 USB 허브 사용 권장
