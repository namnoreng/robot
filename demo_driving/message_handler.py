"""
메시지 처리 모듈
외부 클라이언트(앱, 로봇)로부터 받은 메시지를 처리하는 함수들
"""
import find_destination

def handle_server_command(msg, clients, app_clients, robot_clients, save_parking_status, export_parking_status, reset_all_parking):
    """서버에서 직접 입력한 명령 처리 (command_mode용)"""
    # RESET_PARKING 명령 처리
    if msg.strip().upper() == "RESET_PARKING":
        reset_all_parking()
        save_parking_status(export_parking_status())
        print("[서버] 주차장 상태가 초기화되었습니다.")
        return
    
    # 기존 IN/OUT 처리
    try:
        cmd, car_number = msg.split(",")
        cmd = cmd.strip().upper()
        car_number = car_number.strip()
    except Exception:
        print("[서버] 잘못된 메시지 형식")
        return

    if cmd == "IN":
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
    elif cmd == "OUT":
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

def handle_app_message(msg, clients, app_clients, robot_clients, save_parking_status, export_parking_status):
    """앱에서 온 메시지 처리"""
    try:
        cmd, car_number = msg.split(",")
        cmd = cmd.strip().upper()
        car_number = car_number.strip()
    except Exception:
        print("[서버] 잘못된 메시지 형식")
        return

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

def handle_robot_message(msg, clients, app_clients, save_parking_status, export_parking_status):
    """로봇에서 온 메시지 처리"""
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
            find_destination.park_car_at(find_destination.parking_lot, sector, side, subzone, direction, "")
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

def send_parking_status_to_app(client_socket, export_parking_status):
    """앱에 현재 주차 상태를 전송"""
    try:
        parking_status = export_parking_status()
        for car_number, info in parking_status.items():
            android_format = find_destination.convert_to_android_format_full(
                info["sector"], info["side"], info["subzone"], info["direction"]
            )
            message = f"PARKED,{android_format},{car_number}\n"
            client_socket.sendall(message.encode())
            print(f"[서버] 기존 주차 상태 전송: {message.strip()}")
    except Exception as e:
        print(f"[서버] 주차 상태 전송 오류: {e}")

def handle_client(client_socket, addr, clients, app_clients, robot_clients, save_parking_status, export_parking_status):
    """클라이언트 연결 및 메시지 처리"""
    print(f"[+] Connected by {addr}")
    try:
        device_type = client_socket.recv(1024).decode().strip()
        print(f"[{addr}] Device type: {device_type}")
        clients[addr] = (client_socket, device_type)
        
        # 클라이언트 등록
        if device_type == "app":
            # 1번부터 비어있는 번호를 찾아 할당
            app_num = 1
            while app_num in app_clients:
                app_num += 1
            app_clients[app_num] = addr
            print(f"[서버] app #{app_num} 등록: {addr}")
            
            # 새로운 app에 현재 주차 상태 전송
            send_parking_status_to_app(client_socket, export_parking_status)
        elif device_type == "robot":
            robot_num = 1
            while robot_num in robot_clients:
                robot_num += 1
            robot_clients[robot_num] = addr
            print(f"[서버] robot #{robot_num} 등록: {addr}")
        else:
            print(f"[서버] 알 수 없는 타입: {device_type}")
            return

        # 메시지 수신 루프
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            msg = data.decode().strip()
            print(f"[{device_type}][{addr}] Received: {msg}")

            # 메시지 타입별 처리
            if device_type == "app":
                handle_app_message(msg, clients, app_clients, robot_clients, save_parking_status, export_parking_status)
            elif device_type == "robot":
                handle_robot_message(msg, clients, app_clients, save_parking_status, export_parking_status)

    except Exception as e:
        print(f"[{addr}] Error: {e}")
    finally:
        print(f"[-] Disconnected by {addr}")
        # 클라이언트 정리
        for num, a in list(app_clients.items()):
            if a == addr:
                del app_clients[num]
        for num, a in list(robot_clients.items()):
            if a == addr:
                del robot_clients[num]
        if addr in clients:
            del clients[addr]
        client_socket.close()
