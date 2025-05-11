class ParkingSpace:
    def __init__(self):
        self.car_number = None
        
    def is_empty(self):
        return self.car_number is None

class Sector:
    def __init__(self):
        self.left = [ParkingSpace() for _ in range(6)]
        self.right = [ParkingSpace() for _ in range(6)]

parking_lot = [Sector() for _ in range(2)]

def DFS(parking_lot: list):
    # DFS로 비어있는 공간 찾기
    stack = []
    for sector_idx, sector in reversed(list(enumerate(parking_lot))):  # 섹터를 역순으로 추가
        # 오른쪽(right)을 먼저 추가
        stack.extend([(sector_idx, "right", idx, space) for idx, space in reversed(list(enumerate(sector.right)))])
        # 왼쪽(left)을 나중에 추가
        stack.extend([(sector_idx, "left", idx, space) for idx, space in reversed(list(enumerate(sector.left)))])

    while stack:
        sector_idx, direction, space_idx, current = stack.pop()

        if isinstance(current, ParkingSpace) and current.is_empty():
            print(f"섹터 {sector_idx + 1}, 방향 {direction}, 칸 {space_idx + 1}")
            return (sector_idx + 1, direction, space_idx + 1)  # 섹터 번호, 방향, 칸 번호 반환

    print("X")  # 비어있는 공간이 없음
    return None  # 비어있는 공간이 없음을 반환

def find_car(parking_lot: list, car_number: str):
    """
    입력된 차량 번호가 주차된 위치를 반환합니다.
    :param parking_lot: 주차장 데이터
    :param car_number: 찾고자 하는 차량 번호
    :return: (섹터 번호, 방향, 칸 번호) 또는 None
    """
    for sector_idx, sector in enumerate(parking_lot):
        # 왼쪽(left) 탐색
        for idx, space in enumerate(sector.left):
            if space.car_number == car_number:
                print(f"차량 {car_number}은 섹터 {sector_idx + 1}, 방향 left, 칸 {idx + 1}에 있습니다.")
                return (sector_idx + 1, "left", idx + 1)
        # 오른쪽(right) 탐색
        for idx, space in enumerate(sector.right):
            if space.car_number == car_number:
                print(f"차량 {car_number}은 섹터 {sector_idx + 1}, 방향 right, 칸 {idx + 1}에 있습니다.")
                return (sector_idx + 1, "right", idx + 1)

    print(f"차량 {car_number}을 찾을 수 없습니다.")
    return None

def park_car_at(parking_lot: list, sector_idx: int, direction: str, space_idx: int, car_number: str):
    """
    특정 좌표에 차량 번호를 입력하고 상태를 업데이트합니다.
    :param parking_lot: 주차장 데이터
    :param sector_idx: 섹터 번호 (1부터 시작)
    :param direction: 방향 ("left" 또는 "right")
    :param space_idx: 칸 번호 (1부터 시작)
    :param car_number: 주차할 차량 번호
    :return: 성공 여부 (True 또는 False)
    """
    # 섹터 번호와 칸 번호를 0부터 시작하는 인덱스로 변환
    sector_idx -= 1
    space_idx -= 1

    # 유효한 섹터 번호와 방향인지 확인
    if sector_idx < 0 or sector_idx >= len(parking_lot):
        print("Error: Invalid sector index.")
        return False

    if direction not in ["left", "right"]:
        print("Error: Invalid direction.")
        return False

    # 유효한 칸 번호인지 확인
    sector = parking_lot[sector_idx]
    spaces = sector.left if direction == "left" else sector.right
    if space_idx < 0 or space_idx >= len(spaces):
        print("Error: Invalid space index.")
        return False

    # 해당 칸이 비어 있는지 확인
    if not spaces[space_idx].is_empty():
        print(f"Error: Space at sector {sector_idx + 1}, direction {direction}, space {space_idx + 1} is already occupied.")
        return False

    # 차량 번호를 입력하고 상태를 업데이트
    spaces[space_idx].car_number = car_number
    print(f"Vehicle {car_number} parked at sector {sector_idx + 1}, direction {direction}, space {space_idx + 1}.")
    return True

if __name__ == "__main__":
    # 테스트: 모든 공간이 비어있음
    print(DFS(parking_lot))  # 출력: 섹터 1, 방향 left, 칸 1 / 반환값: (1, 'left', 1)

    # 테스트: 첫 번째 섹터의 왼쪽 첫 번째 칸에 차량 주차
    parking_lot[0].left[0].car_number = "1234"
    print(DFS(parking_lot))  # 출력: 섹터 1, 방향 left, 칸 2 / 반환값: (1, 'left', 2)

    # 테스트: 첫 번째 섹터의 모든 왼쪽 칸에 차량 주차
    for space in parking_lot[0].left:
        space.car_number = "5678"
    print(DFS(parking_lot))  # 출력: 섹터 1, 방향 right, 칸 1 / 반환값: (1, 'right', 1)

    # 테스트: 모든 공간이 차 있음
    for sector in parking_lot:
        for space in sector.left + sector.right:
            space.car_number = "5678"
    print(DFS(parking_lot))  # 출력: X / 반환값: None

    # 테스트: 모든 공간이 비어있음
    for sector in parking_lot:
        for space in sector.left + sector.right:
            space.car_number = None
    print(DFS(parking_lot))  # 출력: 섹터 1, 방향 left, 칸 1 / 반환값: (1, 'left', 1)

    # 테스트: 차량 주차
    park_car_at(parking_lot, 1, "left", 1, "1234")  # 섹터 1, 방향 left, 칸 1
    park_car_at(parking_lot, 1, "right", 3, "5678")  # 섹터 1, 방향 right, 칸 3
    park_car_at(parking_lot, 2, "left", 5, "91011")  # 섹터 2, 방향 left, 칸 5

    # 차량 위치 찾기 테스트
    print(find_car(parking_lot, "1234"))  # 출력: 섹터 1, 방향 left, 칸 1 / 반환값: (1, 'left', 1)
    print(find_car(parking_lot, "5678"))  # 출력: 섹터 1, 방향 right, 칸 3 / 반환값: (1, 'right', 3)
    print(find_car(parking_lot, "91011"))  # 출력: 섹터 2, 방향 left, 칸 5 / 반환값: (2, 'left', 5)
    print(find_car(parking_lot, "0000"))  # 출력: 차량 0000을 찾을 수 없습니다. / 반환값: None