"""
간단한 색상 마커 사용법

ArUco가 작동하지 않으므로 색상 마커 시스템을 사용합니다.

마커 제작 방법:
1. 빨간색 종이/스티커 - ID 0 (정지)
2. 초록색 종이/스티커 - ID 1 (전진/회전)  
3. 파란색 종이/스티커 - ID 2 (후진)
4. 빨간색 + 초록색 (근처에) - ID 3
5. 빨간색 + 파란색 (근처에) - ID 4
6. 초록색 + 파란색 (근처에) - ID 5

마커 크기: 최소 3cm x 3cm 이상
색상: 선명한 색상 사용 (채도 높게)

로봇 제어:
- ID 0 (빨강): 정지
- ID 1 (초록): 중앙이면 전진, 좌측이면 좌회전, 우측이면 우회전  
- ID 2 (파랑): 후진

테스트 방법:
1. python3 simple_marker_detection.py  (마커만 테스트)
2. python3 detect_aruco_safe.py       (로봇 제어 포함)
3. python3 default_setting.py         (전체 시스템)

주의사항:
- 조명이 좋은 곳에서 사용
- 배경과 구분되는 색상 사용
- 카메라와 1-2미터 거리에서 테스트
"""

print("색상 마커 시스템 설명서")
print("="*50)
with open(__file__, 'r', encoding='utf-8') as f:
    content = f.read()
    start = content.find('"""') + 3
    end = content.rfind('"""')
    doc = content[start:end]
    print(doc)
