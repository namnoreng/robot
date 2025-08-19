import socket
import threading
import json
import os

# 개인적으로 만든 모듈 불러오기
import find_destination
import message_handler
HOST = '0.0.0.0'
PORT = 12345

clients = {}  # {addr: (client_socket, device_type)}
app_clients = {}  # {번호: addr}
robot_clients = {}  # {번호: addr}
app_counter = 1
robot_counter = 1

PARKING_STATUS_FILE = "parking_status.json"

def save_parking_status(parking_lot):
    """주차 상태를 JSON 파일로 저장 - 현재 비활성화"""
    # JSON 저장 기능 비활성화 (load를 통한 상태 업데이트만 사용)
    # try:
    #     status = export_parking_status()
    #     with open(PARKING_STATUS_FILE, "w", encoding="utf-8") as f:
    #         json.dump(status, f, ensure_ascii=False, indent=2)
    #     print(f"[서버] 주차 상태 저장 완료: {len(status)}대 차량")
    #     return True
    # except Exception as e:
    #     print(f"[서버] 주차 상태 저장 실패: {e}")
    #     return False
    pass

def load_parking_status():
    """JSON 파일에서 주차 상태를 불러옴"""
    try:
        if os.path.exists(PARKING_STATUS_FILE):
            with open(PARKING_STATUS_FILE, "r", encoding="utf-8") as f:
                status = json.load(f)
            print(f"[서버] 주차 상태 파일 로드 성공: {len(status)}대 차량")
            return status
        else:
            print(f"[서버] 주차 상태 파일이 없습니다: {PARKING_STATUS_FILE}")
            return {}
    except json.JSONDecodeError as e:
        print(f"[서버] 주차 상태 파일 파싱 오류: {e}")
        return {}
    except Exception as e:
        print(f"[서버] 주차 상태 파일 로드 실패: {e}")
        return {}

# 서버 시작 시 기존 주차 상태 복원
parking_status = load_parking_status()
print(f"[서버] 기존 주차 상태 로드: {len(parking_status)}대 차량")

# 기존 주차 상태를 parking_lot에 복원
for car_number, info in parking_status.items():
    try:
        find_destination.park_car_at(
            find_destination.parking_lot,
            info["sector"], info["side"], info["subzone"], info["direction"], car_number
        )
        print(f"[서버] 차량 {car_number} 복원: sector {info['sector']}, {info['side']}, subzone {info['subzone']}, {info['direction']}")
    except KeyError as e:
        print(f"[서버] 차량 {car_number} 복원 실패 - 잘못된 키: {e}")
    except Exception as e:
        print(f"[서버] 차량 {car_number} 복원 실패: {e}")

def reset_all_parking():
    # 모든 공간을 비움
    for sector in find_destination.parking_lot:
        for side in ["left", "right"]:
            subzones = getattr(sector, side)
            for subzone in subzones:
                for direction in ["left", "right"]:
                    space = getattr(subzone, direction)
                    space.car_number = None
    print("[서버] 모든 주차공간이 초기화되었습니다.")

def command_mode():
    print("[서버] 명령어 모드 시작")
    print("사용법:")
    print("  - [app|robot|server] 번호 메시지")
    print("  - exit: 종료")
    print("예시: app 1 test_message, robot 1 PARK,1,left,1,left,1234, server 1 IN,1234")
    
    while True:
        cmd = input("[서버] 명령 입력: ").strip()
        
        if cmd.lower() == "exit":
            print("[서버] 명령어 입력 종료")
            break
            
        try:
            parts = cmd.split()
            if len(parts) < 3:
                print("[서버] 입력 형식: [app|robot|server] 번호 메시지")
                continue
                
            target_type, num, msg = parts[0], int(parts[1]), " ".join(parts[2:])
            
            if target_type == "app":
                if num in app_clients:
                    target_addr = app_clients[num]
                    clients[target_addr][0].sendall((msg + '\n').encode())
                    print(f"[서버] app #{num}({target_addr})에게 메시지 전송: {msg}")
                else:
                    print(f"[서버] 해당 app 번호 없음: {num}")
            elif target_type == "robot":
                if num in robot_clients:
                    target_addr = robot_clients[num]
                    clients[target_addr][0].sendall((msg + '\n').encode())
                    print(f"[서버] robot #{num}({target_addr})에게 메시지 전송: {msg}")
                else:
                    print(f"[서버] 해당 robot 번호 없음: {num}")
            elif target_type == "server":
                message_handler.handle_server_command(msg, clients, app_clients, robot_clients, save_parking_status, export_parking_status, reset_all_parking)
            else:
                print("[서버] 대상은 app, robot, server만 가능합니다.")
        except Exception as e:
            print(f"[서버] 오류: {e}")

def export_parking_status():
    """현재 주차 상태를 딕셔너리 형태로 추출"""
    status = {}
    try:
        for sector_idx, sector in enumerate(find_destination.parking_lot):
            for side in ["left", "right"]:
                subzones = getattr(sector, side)
                for subzone_idx, subzone in enumerate(subzones):
                    for direction in ["left", "right"]:
                        space = getattr(subzone, direction)
                        if space.car_number:
                            status[space.car_number] = {
                                "sector": sector_idx + 1,
                                "side": side,
                                "subzone": subzone_idx + 1,
                                "direction": direction
                            }
        
        print(f"[서버] 현재 주차 상태: {len(status)}대 차량")
        for car_number, info in status.items():
            print(f"  - {car_number}: sector {info['sector']}, {info['side']}, subzone {info['subzone']}, {info['direction']}")
            
    except Exception as e:
        print(f"[서버] 주차 상태 추출 오류: {e}")
    
    return status

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[*] Server listening on {HOST}:{PORT}")

    threading.Thread(target=command_mode, daemon=True).start()

    try:
        while True:
            client_socket, addr = server.accept()
            thread = threading.Thread(
                target=message_handler.handle_client, 
                args=(client_socket, addr, clients, app_clients, robot_clients, save_parking_status, export_parking_status), 
                daemon=True
            )
            thread.start()
    except KeyboardInterrupt:
        print("\n[!] Server shutting down.")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()