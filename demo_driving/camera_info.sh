#!/bin/bash

echo "=== Jetson Nano 카메라 진단 스크립트 ==="
echo ""

# V4L2 유틸리티 설치 확인
echo "📦 V4L2 유틸리티 설치 중..."
sudo apt update
sudo apt install -y v4l2-utils

echo ""
echo "=== 카메라 장치 목록 ==="
v4l2-ctl --list-devices

echo ""
echo "=== 카메라 지원 형식 (중요!) ==="
v4l2-ctl --list-formats-ext

echo ""
echo "=== 현재 카메라 설정 ==="
v4l2-ctl --all

echo ""
echo "=== USB 장치 정보 ==="
lsusb | grep -i camera

echo ""
echo "=== dmesg 카메라 로그 ==="
dmesg | grep -i camera | tail -10

echo ""
echo "=== 진단 완료 ==="
echo "위 정보를 확인하여 카메라가 실제로 지원하는 해상도를 파악하세요."
