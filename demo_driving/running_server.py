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

def handle_client(client_socket, addr):
    print(f"[+] Connected by {addr}")
    try:
        device_type = client_socket.recv(1024).decode().strip()
        print(f"[{addr}] Device type: {device_type}")
        clients[addr] = (client_socket, device_type)
        if device_type == "app":
            # 1번부터 비어있는 번호를 찾아 할당
            app_num = 1
            while app_num in app_clients:
                app_num += 1
            app_clients[app_num] = addr
            print(f"[서버] app #{app_num} 등록: {addr}")
        elif device_type == "robot":
            robot_num = 1
            while robot_num in robot_clients:
                robot_num += 1
            robot_clients[robot_num] = addr
            print(f"[서버] robot #{robot_num} 등록: {addr}")
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
                        # === 여기서 앱에 메시지 전송 ===
                        android_format = find_destination.convert_to_android_format_full(sector, side, subzone, direction)
                        if 1 in app_clients:
                            app_addr = app_clients[1]
                            app_sock = clients[app_addr][0]
                            app_sock.sendall(f"PARKED,{android_format},{car_number}\n".encode())
                        save_parking_status(export_parking_status())
                    else:
                        print("[서버] 빈자리가 없습니다.")
                elif cmd == "OUT":
                    # 차량 위치 찾기
                    result = find_destination.find_car(find_destination.parking_lot, car_number)
                    if result:
                        sector, side, subzone, direction = result
                        # 자리는 로봇이 OUT_DONE을 보낼 때까지 비우지 않음
                        print(f"[서버] 차량 {car_number} 출차 요청: {sector},{side},{subzone},{direction}")
                        # 로봇에게 명령 전달 예시
                        if 1 in robot_clients:
                            robot_addr = robot_clients[1]
                            robot_sock = clients[robot_addr][0]
                            robot_sock.sendall(f"OUT,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                    else:
                        print(f"[서버] 차량 {car_number}의 위치를 찾을 수 없습니다.")
                else:
                    print("[서버] 알 수 없는 명령")
            elif device_type == "robot":
                # 로봇에서 온 메시지 처리
                # 예: DONE,1,left,1,left,1111
                if msg.startswith("DONE"):
                    try:
                        _, sector, side, subzone, direction, car_number = msg.split(",")
                        android_format = find_destination.convert_to_android_format_full(sector, side, subzone, direction)
                        # parked 메시지 앱에 전송
                        if 1 in app_clients:
                            app_addr = app_clients[1]
                            app_sock = clients[app_addr][0]
                            app_sock.sendall(f"parked,{android_format},{car_number}\n".encode())
                            print(f"[서버] parked,{android_format},{car_number} → 앱에 전송")
                    except Exception as e:
                        print(f"[서버] DONE 메시지 파싱 오류: {e}")
                elif msg.startswith("OUT_DONE"):
                    try:
                        # 출차 완료: OUT_DONE,1,left,1,left,1111
                        _, sector, side, subzone, direction, car_number = msg.split(",")
                        # 실제로 자리 비우기 (로봇이 출차 완료했으므로)
                        sector_idx = int(sector) - 1
                        subzone_idx = int(subzone) - 1
                        target_space = getattr(find_destination.parking_lot[sector_idx], side)[subzone_idx]
                        space = getattr(target_space, direction)
                        space.car_number = None  # 자리 비우기
                        print(f"[서버] 차량 {car_number}를 {sector},{side},{subzone},{direction}에서 출차 완료")
                        
                        android_format = find_destination.convert_to_android_format_full(sector, side, subzone, direction)
                        # lifted 메시지 앱에 전송
                        if 1 in app_clients:
                            app_addr = app_clients[1]
                            app_sock = clients[app_addr][0]
                            app_sock.sendall(f"lifted,{android_format},{car_number}\n".encode())
                            print(f"[서버] lifted,{android_format},{car_number} → 앱에 전송")
                        
                        # 출차 완료 후 주차장 상태 저장
                        save_parking_status(export_parking_status())
                    except Exception as e:
                        print(f"[서버] OUT_DONE 메시지 파싱 오류: {e}")
                elif msg.startswith("COMPLETE") or msg.startswith("done"):
                    # 전체 작업 완료 (대기 위치 복귀 완료)
                    if 1 in app_clients:
                        app_addr = app_clients[1]
                        app_sock = clients[app_addr][0]
                        app_sock.sendall(f"COMPLETE\n".encode())
                        print(f"[서버] COMPLETE → 앱에 전송")
                elif msg.startswith("sector_arrived") or msg.startswith("subzone_arrived") or msg.startswith("starting_point"):
                    try:
                        # 형식: sector_arrived,1,None,None 또는 subzone_arrived,1,left,1 또는 starting_point,0,None,None
                        parts = msg.split(",")
                        arrival_type = parts[0]
                        sector = int(parts[1]) if parts[1] != "None" else None
                        side = parts[2] if parts[2] != "None" else None
                        subzone = int(parts[3]) if parts[3] != "None" else None
                        
                        # find_destination의 convert_to_android_format 함수 사용
                        if arrival_type == "starting_point":
                            android_format = find_destination.convert_to_android_format(0, None, None)  # "waiting_point"
                        elif arrival_type == "sector_arrived":
                            android_format = find_destination.convert_to_android_format(sector, None, None)  # "aMM"
                        elif arrival_type == "subzone_arrived":
                            android_format = find_destination.convert_to_android_format(sector, side, subzone)  # "aLa"나 "aLb"
                        
                        # 현재 위치를 앱에 MOVE 메시지로 전송
                        if 1 in app_clients:
                            app_addr = app_clients[1]
                            app_sock = clients[app_addr][0]
                            app_sock.sendall(f"MOVE,{android_format}\n".encode())
                            print(f"[서버] MOVE,{android_format} → 앱에 전송")
                    except Exception as e:
                        print(f"[서버] 위치 업데이트 메시지 파싱 오류: {e}")
                # 필요시 다른 로봇 메시지도 처리

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
                    # RESET_PARKING 명령 추가
                    if msg.strip().upper() == "RESET_PARKING":
                        reset_all_parking()
                        save_parking_status(export_parking_status())
                        print("[서버] 주차장 상태가 초기화되었습니다.")
                        continue
                    # 기존 IN/OUT 처리
                    try:
                        cmd2, car_number = msg.split(",")
                        cmd2 = cmd2.strip().upper()
                        car_number = car_number.strip()
                    except Exception:
                        print("[서버] 잘못된 메시지 형식")
                        continue

                    if cmd2 == "IN":
                        result = find_destination.DFS(find_destination.parking_lot)
                        if result:
                            sector, side, subzone, direction = result
                            find_destination.park_car_at(find_destination.parking_lot, sector, side, subzone, direction, car_number)
                            print(f"[서버] 차량 {car_number}를 {sector},{side},{subzone},{direction}에 주차")
                            if 1 in robot_clients:
                                robot_addr = robot_clients[1]
                                robot_sock = clients[robot_addr][0]
                                robot_sock.sendall(f"PARK,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                            android_format = find_destination.convert_to_android_format_full(sector, side, subzone, direction)
                            if 1 in app_clients:
                                app_addr = app_clients[1]
                                app_sock = clients[app_addr][0]
                                app_sock.sendall(f"PARKED,{android_format},{car_number}\n".encode())
                            save_parking_status(export_parking_status())
                        else:
                            print("[서버] 빈자리가 없습니다.")
                    elif cmd2 == "OUT":
                        result = find_destination.find_car(find_destination.parking_lot, car_number)
                        if result:
                            sector, side, subzone, direction = result
                            # 자리는 로봇이 OUT_DONE을 보낼 때까지 비우지 않음
                            print(f"[서버] 차량 {car_number} 출차 요청: {sector},{side},{subzone},{direction}")
                            if 1 in robot_clients:
                                robot_addr = robot_clients[1]
                                robot_sock = clients[robot_addr][0]
                                robot_sock.sendall(f"OUT,{sector},{side},{subzone},{direction},{car_number}\n".encode())
                        else:
                            print(f"[서버] 차량 {car_number}의 위치를 찾을 수 없습니다.")
                    else:
                        print("[서버] 알 수 없는 명령")
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
            thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[!] Server shutting down.")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()