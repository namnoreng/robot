import socket
import threading
import json
import os

# 개인적으로 만든 모듈 불러오기
import find_destination
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
    with open(PARKING_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(parking_lot, f, ensure_ascii=False, indent=2)

def load_parking_status():
    if os.path.exists(PARKING_STATUS_FILE):
        with open(PARKING_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 서버 시작 시
parking_status = load_parking_status()
# parking_status = {차량번호: {sector, side, subzone, direction}}
for car_number, info in parking_status.items():
    find_destination.park_car_at(
        find_destination.parking_lot,
        info["sector"], info["side"], info["subzone"], info["direction"], car_number
    )

def handle_client(client_socket, addr):
    global app_counter, robot_counter
    print(f"[+] Connected by {addr}")
    try:
        device_type = client_socket.recv(1024).decode().strip()
        print(f"[{addr}] Device type: {device_type}")
        clients[addr] = (client_socket, device_type)
        if device_type == "app":
            app_clients[app_counter] = addr
            app_num = app_counter
            print(f"[서버] app #{app_counter} 등록: {addr}")
            app_counter += 1
        elif device_type == "robot":
            robot_clients[robot_counter] = addr
            robot_num = robot_counter
            print(f"[서버] robot #{robot_counter} 등록: {addr}")
            robot_counter += 1
        else:
            print(f"[서버] 알 수 없는 타입: {device_type}")
            return

        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            msg = data.decode().strip()
            print(f"[{device_type}][{addr}] Received: {msg}")

            if device_type == "app":
                # IN,차량번호 또는 OUT,차량번호 메시지 처리
                try:
                    cmd, car_number = msg.split(",")
                    cmd = cmd.strip().upper()
                    car_number = car_number.strip()
                except Exception:
                    print("[서버] 잘못된 메시지 형식")
                    continue

                if cmd == "IN":
                    # 빈자리 탐색
                    result = find_destination.DFS(find_destination.parking_lot)
                    if result:
                        sector, side, subzone, direction = result
                        # 자리 배정
                        find_destination.park_car_at(find_destination.parking_lot, sector, side, subzone, direction, car_number)
                        print(f"[서버] 차량 {car_number}를 {sector},{side},{subzone},{direction}에 주차")
                        # 로봇에게 목적지 정보 포함 명령 전송
                        if 1 in robot_clients:
                            robot_addr = robot_clients[1]
                            robot_sock = clients[robot_addr][0]
                            robot_sock.sendall(f"PARK,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                        save_parking_status(export_parking_status())
                    else:
                        print("[서버] 빈자리가 없습니다.")
                elif cmd == "OUT":
                    # 차량 위치 찾기
                    result = find_destination.find_car(find_destination.parking_lot, car_number)
                    if result:
                        sector, side, subzone, direction = result
                        # 자리 비우기
                        find_destination.park_car_at(find_destination.parking_lot, sector, side, subzone, direction, "")
                        print(f"[서버] 차량 {car_number}를 {sector},{side},{subzone},{direction}에서 출차")
                        # 로봇에게 명령 전달 예시
                        if 1 in robot_clients:
                            robot_addr = robot_clients[1]
                            robot_sock = clients[robot_addr][0]
                            robot_sock.sendall(f"OUT,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                        # 차량 출차 정보 저장
                        save_parking_status(export_parking_status())
                    else:
                        print(f"[서버] 차량 {car_number}의 위치를 찾을 수 없습니다.")
                else:
                    print("[서버] 알 수 없는 명령")
            # 로봇에서 온 응답을 앱에게 전달하려면 여기에 추가

    except Exception as e:
        print(f"[{addr}] Error: {e}")
    finally:
        print(f"[-] Disconnected by {addr}")
        for num, a in list(app_clients.items()):
            if a == addr:
                del app_clients[num]
        for num, a in list(robot_clients.items()):
            if a == addr:
                del robot_clients[num]
        if addr in clients:
            del clients[addr]
        client_socket.close()

def command_mode():
    global mode
    while True:
        cmd = input("모드 입력 (register/send/exit 또는 [app|robot]번호 메시지): ").strip()
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
            # 메시지 입력 처리
            try:
                # 입력 예시: app 1 메시지내용   또는   robot 2 메시지내용
                parts = cmd.split()
                if len(parts) < 3:
                    print("[서버] 입력 형식: [app|robot] 번호 메시지")
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
                else:
                    print("[서버] 대상은 app 또는 robot만 가능합니다.")
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
            thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[!] Server shutting down.")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()