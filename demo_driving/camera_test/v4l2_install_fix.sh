#!/bin/bash

echo "=== V4L2-Utils 설치 문제 해결 스크립트 ==="
echo ""

# 현재 시스템 정보 확인
echo "📋 시스템 정보:"
uname -a
lsb_release -a 2>/dev/null || cat /etc/os-release

echo ""
echo "=== 1. 패키지 저장소 업데이트 ==="
sudo apt update

echo ""
echo "=== 2. 다양한 방법으로 v4l2-utils 설치 시도 ==="

echo "🔧 방법 1: 기본 패키지 설치"
sudo apt install -y v4l2-utils
if command -v v4l2-ctl &> /dev/null; then
    echo "✅ 방법 1 성공!"
    v4l2-ctl --version
else
    echo "❌ 방법 1 실패"
fi

echo ""
echo "🔧 방법 2: universe 저장소 추가 후 설치"
sudo add-apt-repository universe
sudo apt update
sudo apt install -y v4l2-utils
if command -v v4l2-ctl &> /dev/null; then
    echo "✅ 방법 2 성공!"
    v4l2-ctl --version
else
    echo "❌ 방법 2 실패"
fi

echo ""
echo "🔧 방법 3: 직접 패키지 다운로드"
wget http://archive.ubuntu.com/ubuntu/pool/main/v/v4l-utils/v4l-utils_1.18.0-2build1_arm64.deb
if [ -f "v4l-utils_1.18.0-2build1_arm64.deb" ]; then
    sudo dpkg -i v4l-utils_1.18.0-2build1_arm64.deb
    sudo apt install -f  # 의존성 해결
    if command -v v4l2-ctl &> /dev/null; then
        echo "✅ 방법 3 성공!"
        v4l2-ctl --version
    else
        echo "❌ 방법 3 실패"
    fi
else
    echo "❌ 패키지 다운로드 실패"
fi

echo ""
echo "🔧 방법 4: 소스 컴파일"
if ! command -v v4l2-ctl &> /dev/null; then
    echo "소스에서 컴파일을 시도합니다..."
    sudo apt install -y build-essential git autotools-dev autoconf libtool
    git clone https://git.linuxtv.org/v4l-utils.git
    cd v4l-utils
    ./bootstrap.sh
    ./configure
    make -j4
    sudo make install
    cd ..
    
    if command -v v4l2-ctl &> /dev/null; then
        echo "✅ 방법 4 성공!"
        v4l2-ctl --version
    else
        echo "❌ 방법 4 실패"
    fi
fi

echo ""
echo "=== 3. v4l2-utils 없이도 카메라 정보 확인하는 방법 ==="

echo "📋 /dev/video* 장치 확인:"
ls -la /dev/video*

echo ""
echo "📋 USB 카메라 장치:"
lsusb | grep -i camera

echo ""
echo "📋 dmesg 로그에서 카메라 정보:"
dmesg | grep -i "video\|camera\|uvc" | tail -10

echo ""
echo "📋 /sys 파일시스템에서 카메라 정보:"
if [ -d "/sys/class/video4linux" ]; then
    for device in /sys/class/video4linux/video*; do
        if [ -d "$device" ]; then
            echo "장치: $(basename $device)"
            if [ -f "$device/name" ]; then
                echo "  이름: $(cat $device/name)"
            fi
            if [ -f "$device/dev" ]; then
                echo "  장치번호: $(cat $device/dev)"
            fi
        fi
    done
fi

echo ""
echo "=== 설치 완료 및 테스트 ==="
if command -v v4l2-ctl &> /dev/null; then
    echo "🎉 v4l2-utils 설치 성공!"
    echo ""
    echo "사용 가능한 명령어:"
    echo "v4l2-ctl --list-devices"
    echo "v4l2-ctl --list-formats-ext"
    echo "v4l2-ctl --all"
else
    echo "⚠️  v4l2-utils 설치 실패"
    echo "하지만 위의 기본 정보로도 카메라 상태를 확인할 수 있습니다."
fi
