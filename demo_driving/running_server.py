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
mode = "register"

PARKING_STATUS_FILE = "parking_status.json"

def save_parking_status(parking_lot):
    # json 저장 비활성화
    # with open(PARKING_STATUS_FILE, "w", encoding="utf-8") as f:
    #     json.dump(parking_lot, f, ensure_ascii=False, indent=2)
    pass

def load_parking_status():
    # json 불러오기 비활성화
    # if os.path.exists(PARKING_STATUS_FILE):
    #     with open(PARKING_STATUS_FILE, "r", encoding="utf-8") as f:
    #         return json.load(f)
    return {}

# 서버 시작 시
parking_status = load_parking_status()
# parking_status = {차량번호: {sector, side, subzone, direction}}
for car_number, info in parking_status.items():
    find_destination.park_car_at(
        find_destination.parking_lot,
        info["sector"], info["side"], info["subzone"], info["direction"], car_number
    )

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
    global mode
    while True:
        cmd = input("모드 입력 (register/send/exit 또는 [app|robot|server]번호 메시지): ").strip()
        if cmd == "register":
            mode = "register"
            print("[서버] 신규 기기 등록 모드로 변경")
        elif cmd == "send":
            mode = "send"
            print("[서버] 메시지 전송 모드로 변경")
        elif cmd == "exit":
            print("[서버] 명령어 입력 종료")
            break
        elif mode == "send":
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
        else:
            print("[서버] 알 수 없는 명령입니다.")

def export_parking_status():
    status = {}
    for sector_idx, sector in enumerate(find_destination.parking_lot):
        for side in ["left", "right"]:
            subzones = getattr(sector, side)
            for subzone_idx, subzone in enumerate(subzones):
                for direction in ["left", "right"]:
                    space = getattr(subzone, direction)
                    if space.car_number:
                        status[space.car_number] = {
                            "sector": sector_idx+1,
                            "side": side,
                            "subzone": subzone_idx+1,
                            "direction": direction
                        }
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