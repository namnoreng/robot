class ParkingSpace:
    def __init__(self):
        self.car_number = None

    def is_empty(self):
        return self.car_number is None

class SubZone:
    def __init__(self):
        self.left = ParkingSpace()
        self.right = ParkingSpace()

class Sector:
    def __init__(self):
        self.left = [SubZone() for _ in range(2)]   # 왼쪽에 2개 subzone
        self.right = [SubZone() for _ in range(2)]  # 오른쪽에 2개 subzone

parking_lot = [Sector() for _ in range(2)]

def convert_to_android_format(sector, side, subzone):
    if sector == 0:
        return "waiting_point"
    elif sector is not None and side is None and subzone is None:
        # sector만 있는 경우 (sector 도착) - aMM 형식
        sector_chr = chr(ord('a') + int(sector) - 1)
        return f"{sector_chr}MM"  # 중앙영역(M) + subzone None/0(M)
    elif sector is not None and side is not None and subzone is not None:
        # 완전한 좌표
        sector_chr = chr(ord('a') + int(sector) - 1)
        
        if side == 'left':
            side_chr = 'L'
        elif side == 'right':
            side_chr = 'R'
        elif side == 'Middle':
            side_chr = 'M'
        
        if subzone == 0:
            subzone_chr = 'M'
        else:
            subzone_chr = chr(ord('a') + int(subzone) - 1)
        return f"{sector_chr}{side_chr}{subzone_chr}"
    else:
        return "unknown"

def convert_to_android_format_full(sector, side, subzone, direction):
    """4자리 좌표를 안드로이드 형식으로 변환 (parked, lifted 메시지용)"""
    if sector == 0:
        return "waiting_point"
    
    # 완전한 좌표 (sector, side, subzone, direction)
    sector_chr = chr(ord('a') + int(sector) - 1)
    
    if side == 'left':
        side_chr = 'L'
    elif side == 'right':
        side_chr = 'R'
    elif side == 'Middle':
        side_chr = 'M'
    
    if subzone == 0:
        subzone_chr = 'M'
    else:
        subzone_chr = chr(ord('a') + int(subzone) - 1)
    
    if direction == 'left':
        direction_chr = 'L'
    elif direction == 'right':
        direction_chr = 'R'
    elif direction == 'Middle':
        direction_chr = 'M'
    
    return f"{sector_chr}{side_chr}{subzone_chr}{direction_chr}"

def DFS(parking_lot: list):
    # 섹터의 left(subzone)부터, 각 subzone의 left/right를 순서대로 탐색
    for sector_idx, sector in enumerate(parking_lot):
        for side in ["left", "right"]:
            subzones = getattr(sector, side)
            for subzone_idx, subzone in enumerate(subzones):
                for direction in ["left", "right"]:
                    space = getattr(subzone, direction)
                    if space.is_empty():
                        print(f"섹터 {sector_idx+1}, 방향 {side}, subzone {subzone_idx+1}, 방향 {direction}")
                        return (sector_idx+1, side, subzone_idx+1, direction)
    print("X")
    return None

def find_car(parking_lot: list, car_number: str):
    for sector_idx, sector in enumerate(parking_lot):
        for side in ["left", "right"]:
            subzones = getattr(sector, side)
            for subzone_idx, subzone in enumerate(subzones):
                for direction in ["left", "right"]:
                    space = getattr(subzone, direction)
                    if space.car_number == car_number:
                        print(f"차량 {car_number}은 섹터 {sector_idx+1}, 방향 {side}, subzone {subzone_idx+1}, 방향 {direction}에 있습니다.")
                        return (sector_idx+1, side, subzone_idx+1, direction)
    print(f"차량 {car_number}을 찾을 수 없습니다.")
    return None

def park_car_at(parking_lot: list, sector_idx: int, side: str, subzone_idx: int, direction: str, car_number: str = ""):
    sector_idx -= 1
    subzone_idx -= 1
    if side not in ["left", "right"] or direction not in ["left", "right"]:
        print("Error: side와 direction은 left 또는 right여야 합니다.")
        return False
    subzone = getattr(parking_lot[sector_idx], side)[subzone_idx]
    space = getattr(subzone, direction)
    if not space.is_empty():
        print("Error: 이미 주차된 공간입니다.")
        return False
    space.car_number = car_number
    print(f"Vehicle {car_number} parked at sector {sector_idx+1}, {side}, subzone {subzone_idx+1}, {direction}.")
    return True

if __name__ == "__main__":
    # 테스트: 모든 공간이 비어있음
    print(DFS(parking_lot))  # 섹터 1, 방향 left, subzone 1, 방향 left

    # 테스트: 첫 번째 섹터의 첫 번째 subzone의 left에 차량 주차
    parking_lot[0].left[0].left.car_number = "1234"
    print(DFS(parking_lot))  # 섹터 1, 방향 left, subzone 1, 방향 right

    # 모든 공간 채우기 테스트
    for sector in parking_lot:
        for side in ["left", "right"]:
            for subzone in getattr(sector, side):
                subzone.left.car_number = "5678"
                subzone.right.car_number = "5678"
    print(DFS(parking_lot))  # X

    # 모든 공간 비우기
    for sector in parking_lot:
        for side in ["left", "right"]:
            for subzone in getattr(sector, side):
                subzone.left.car_number = None
                subzone.right.car_number = None
    print(DFS(parking_lot))  # 섹터 1, 방향 left, subzone 1, 방향 left

    # 차량 주차 테스트
    park_car_at(parking_lot, 1, "left", 1, "left", car_number="1234")  # 섹터 1, left, subzone 1, left

    # 차량 위치 찾기 테스트
    print(find_car(parking_lot, "1234"))  # 섹터 1, 방향 left, subzone 1, 방향 left
    print(find_car(parking_lot, "0000"))  # 차량 0000을 찾을 수 없습니다.