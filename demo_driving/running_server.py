import socket
import threading

HOST = '0.0.0.0'
PORT = 12345

clients = {}  # {addr: (client_socket, device_type)}

def handle_client(client_socket, addr):
    print(f"[+] Connected by {addr}")
    device_type = None
    try:
        # 첫 메시지를 타입(app/robot)으로 받음
        device_type = client_socket.recv(1024).decode().strip()
        print(f"[{addr}] Device type: {device_type}")
        clients[addr] = (client_socket, device_type)
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
        if addr in clients:
            del clients[addr]
        client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[*] Server listening on {HOST}:{PORT}")

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