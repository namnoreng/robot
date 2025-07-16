import socket
import threading

HOST = '0.0.0.0'  # 모든 인터페이스에서 접속 허용
PORT = 12345      # 사용할 포트 번호

def handle_client(client_socket, addr):
    print(f"[+] Connected by {addr}")
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            print(f"[{addr}] Received: {data.decode().strip()}")
            client_socket.sendall(data)  # 에코 서버처럼 받은 데이터를 다시 보냄
    except Exception as e:
        print(f"[{addr}] Error: {e}")
    finally:
        print(f"[-] Disconnected by {addr}")
        client_socket.close()

def main():
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
    main()