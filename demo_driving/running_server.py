import socket
import threading

HOST = '0.0.0.0'
PORT = 12345

clients = {}  # {addr: (client_socket, device_type)}
app_clients = {}  # {번호: addr}
app_counter = 1
mode = "register"

def handle_client(client_socket, addr):
    global app_counter
    print(f"[+] Connected by {addr}")
    try:
        device_type = client_socket.recv(1024).decode().strip()
        print(f"[{addr}] Device type: {device_type}")
        clients[addr] = (client_socket, device_type)
        if device_type == "app":
            app_clients[app_counter] = addr
            print(f"[서버] app #{app_counter} 등록: {addr}")
            app_counter += 1
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            print(f"[{device_type}][{addr}] Received: {data.decode().strip()}")
            client_socket.sendall(data)
    except Exception as e:
        print(f"[{addr}] Error: {e}")
    finally:
        print(f"[-] Disconnected by {addr}")
        # app_clients에서 제거
        for num, a in list(app_clients.items()):
            if a == addr:
                del app_clients[num]
        if addr in clients:
            del clients[addr]
        client_socket.close()

def command_mode():
    global mode
    while True:
        cmd = input("모드 입력 (register/send/exit): ").strip()
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
                # app 번호와 메시지 입력: 예) 1 Hello app!
                parts = cmd.split()
                if len(parts) < 2:
                    print("[서버] 입력 형식: app번호 메시지")
                    continue
                app_num, msg = int(parts[0]), " ".join(parts[1:])
                if app_num in app_clients:
                    target_addr = app_clients[app_num]
                    clients[target_addr][0].sendall(msg.encode())
                    print(f"[서버] app #{app_num}({target_addr})에게 메시지 전송: {msg}")
                else:
                    print(f"[서버] 해당 app 번호 없음: {app_num}")
            except Exception as e:
                print(f"[서버] 오류: {e}")

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