import socket
import threading

HOST = '0.0.0.0'
PORT = 12345

clients = {}  # {addr: (client_socket, device_type)}
app_clients = {}  # {번호: addr}
robot_clients = {}  # {번호: addr}
app_counter = 1
robot_counter = 1
mode = "register"

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

            # 앱에서 온 명령을 로봇에게 중계
            if device_type == "app":
                # 예시: 항상 robot 1에게 전달 (여러 로봇이면 선택 로직 필요)
                if 1 in robot_clients:
                    robot_addr = robot_clients[1]
                    robot_sock = clients[robot_addr][0]
                    robot_sock.sendall((msg + '\n').encode())
                    print(f"[서버] robot #1({robot_addr})에게 명령 전달: {msg}")
                else:
                    print("[서버] 연결된 로봇이 없습니다.")
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