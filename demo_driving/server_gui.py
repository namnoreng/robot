import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import socket
import json
import os
from datetime import datetime
import queue

# 개인적으로 만든 모듈 불러오기
import find_destination
import message_handler

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Parking Server Control Panel")
        self.root.geometry("1200x800")
        
        # 서버 관련 변수
        self.HOST = '0.0.0.0'
        self.PORT = 12345
        self.server_socket = None
        self.is_running = False
        
        # 클라이언트 관리
        self.clients = {}  # {addr: (client_socket, device_type)}
        self.app_clients = {}  # {번호: addr}
        self.robot_clients = {}  # {번호: addr}
        self.app_counter = 1
        self.robot_counter = 1
        
        # 로그 메시지 큐
        self.log_queue = queue.Queue()
        
        # GUI 구성
        self.setup_gui()
        
        # 로그 업데이트 스레드 시작
        self.root.after(100, self.update_logs)
        
        # 서버 자동 시작 여부 묻기
        if messagebox.askyesno("서버 시작", "서버를 자동으로 시작하시겠습니까?"):
            self.start_server()

    def setup_gui(self):
        # 메인 프레임 구성
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 서버 제어 패널
        self.setup_server_control(main_frame)
        
        # 클라이언트 상태 패널
        self.setup_client_status(main_frame)
        
        # 주차 상태 패널
        self.setup_parking_status(main_frame)
        
        # 명령어 패널
        self.setup_command_panel(main_frame)
        
        # 로그 패널
        self.setup_log_panel(main_frame)

    def setup_server_control(self, parent):
        # 서버 제어 프레임
        server_frame = ttk.LabelFrame(parent, text="서버 제어", padding="5")
        server_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 서버 상태 표시
        self.status_label = ttk.Label(server_frame, text="서버 상태: 중지됨", foreground="red")
        self.status_label.grid(row=0, column=0, padx=(0, 10))
        
        # 서버 제어 버튼
        self.start_btn = ttk.Button(server_frame, text="서버 시작", command=self.start_server)
        self.start_btn.grid(row=0, column=1, padx=5)
        
        self.stop_btn = ttk.Button(server_frame, text="서버 중지", command=self.stop_server, state="disabled")
        self.stop_btn.grid(row=0, column=2, padx=5)
        
        # 포트 설정
        ttk.Label(server_frame, text="포트:").grid(row=0, column=3, padx=(20, 5))
        self.port_var = tk.StringVar(value=str(self.PORT))
        port_entry = ttk.Entry(server_frame, textvariable=self.port_var, width=8)
        port_entry.grid(row=0, column=4, padx=5)

    def setup_client_status(self, parent):
        # 클라이언트 상태 프레임
        client_frame = ttk.LabelFrame(parent, text="연결된 클라이언트", padding="5")
        client_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        client_frame.columnconfigure(0, weight=1)
        client_frame.rowconfigure(1, weight=1)
        
        # 클라이언트 리스트
        columns = ("번호", "타입", "주소", "상태")
        self.client_tree = ttk.Treeview(client_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.client_tree.heading(col, text=col)
            self.client_tree.column(col, width=80)
        
        # 스크롤바
        client_scrollbar = ttk.Scrollbar(client_frame, orient="vertical", command=self.client_tree.yview)
        self.client_tree.configure(yscrollcommand=client_scrollbar.set)
        
        self.client_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        client_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # 클라이언트 새로고침 버튼
        ttk.Button(client_frame, text="새로고침", command=self.update_client_list).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

    def setup_parking_status(self, parent):
        # 주차 상태 프레임
        parking_frame = ttk.LabelFrame(parent, text="주차 상태", padding="5")
        parking_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        parking_frame.columnconfigure(0, weight=1)
        parking_frame.rowconfigure(1, weight=1)
        
        # 주차 현황 텍스트
        self.parking_text = scrolledtext.ScrolledText(parking_frame, height=8, width=40)
        self.parking_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 주차 상태 새로고침 버튼
        refresh_frame = ttk.Frame(parking_frame)
        refresh_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Button(refresh_frame, text="새로고침", command=self.update_parking_status).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(refresh_frame, text="모든 주차 초기화", command=self.reset_all_parking).grid(row=0, column=1, padx=5)

    def setup_command_panel(self, parent):
        # 명령어 패널 프레임
        cmd_frame = ttk.LabelFrame(parent, text="명령어 전송", padding="5")
        cmd_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        cmd_frame.columnconfigure(2, weight=1)
        
        # 대상 선택
        ttk.Label(cmd_frame, text="대상:").grid(row=0, column=0, padx=(0, 5))
        self.target_var = tk.StringVar(value="app")
        target_combo = ttk.Combobox(cmd_frame, textvariable=self.target_var, values=["app", "robot", "server"], width=8)
        target_combo.grid(row=0, column=1, padx=(0, 10))
        
        # 번호 입력
        ttk.Label(cmd_frame, text="번호:").grid(row=0, column=2, padx=(0, 5))
        self.number_var = tk.StringVar(value="1")
        number_entry = ttk.Entry(cmd_frame, textvariable=self.number_var, width=5)
        number_entry.grid(row=0, column=3, padx=(0, 10))
        
        # 메시지 입력
        ttk.Label(cmd_frame, text="메시지:").grid(row=0, column=4, padx=(0, 5))
        self.message_var = tk.StringVar()
        message_entry = ttk.Entry(cmd_frame, textvariable=self.message_var, width=40)
        message_entry.grid(row=0, column=5, padx=(0, 10), sticky=(tk.W, tk.E))
        message_entry.bind("<Return>", lambda e: self.send_command())
        
        # 전송 버튼
        ttk.Button(cmd_frame, text="전송", command=self.send_command).grid(row=0, column=6)
        
        # 빠른 명령어 버튼들
        quick_frame = ttk.Frame(cmd_frame)
        quick_frame.grid(row=1, column=0, columnspan=7, sticky=(tk.W, tk.E), pady=(10, 0))
        
        quick_commands = [
            ("주차 상태 조회", "server 1 STATUS"),
            ("모든 클라이언트 목록", "server 1 LIST"),
            ("로봇 정지", "robot 1 9"),
            ("로봇 전진", "robot 1 1"),
            ("로봇 후진", "robot 1 2"),
        ]
        
        for i, (text, cmd) in enumerate(quick_commands):
            ttk.Button(quick_frame, text=text, 
                      command=lambda c=cmd: self.quick_command(c)).grid(row=0, column=i, padx=2)

    def setup_log_panel(self, parent):
        # 로그 패널 프레임
        log_frame = ttk.LabelFrame(parent, text="서버 로그", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        
        # 로그 제어 버튼
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        ttk.Button(log_control_frame, text="로그 지우기", command=self.clear_logs).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(log_control_frame, text="로그 저장", command=self.save_logs).grid(row=0, column=1)
        
        # 로그 텍스트 영역
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state="disabled")
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def add_log(self, message):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_queue.put(log_entry)

    def update_logs(self):
        """로그 텍스트 업데이트"""
        try:
            while True:
                log_entry = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert(tk.END, log_entry)
                self.log_text.see(tk.END)
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        
        # 다음 업데이트 예약
        self.root.after(100, self.update_logs)

    def start_server(self):
        """서버 시작"""
        try:
            self.PORT = int(self.port_var.get())
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.HOST, self.PORT))
            self.server_socket.listen(5)
            
            self.is_running = True
            self.status_label.config(text=f"서버 상태: 실행 중 ({self.HOST}:{self.PORT})", foreground="green")
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            
            self.add_log(f"서버 시작: {self.HOST}:{self.PORT}")
            
            # 서버 수락 스레드 시작
            threading.Thread(target=self.accept_clients, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("오류", f"서버 시작 실패: {e}")
            self.add_log(f"서버 시작 실패: {e}")

    def stop_server(self):
        """서버 중지"""
        self.is_running = False
        
        # 모든 클라이언트 연결 종료
        for addr, (client_socket, device_type) in list(self.clients.items()):
            try:
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        self.app_clients.clear()
        self.robot_clients.clear()
        
        # 서버 소켓 종료
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        self.status_label.config(text="서버 상태: 중지됨", foreground="red")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
        self.add_log("서버 중지됨")
        self.update_client_list()

    def accept_clients(self):
        """클라이언트 연결 수락"""
        while self.is_running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.add_log(f"새 연결: {addr}")
                
                # 클라이언트 처리 스레드 시작
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
                
            except Exception as e:
                if self.is_running:
                    self.add_log(f"클라이언트 수락 오류: {e}")
                break

    def handle_client(self, client_socket, addr):
        """클라이언트 메시지 처리"""
        try:
            # 첫 번째 메시지로 디바이스 타입 확인
            data = client_socket.recv(1024).decode().strip()
            device_type = data
            
            if device_type == "app":
                client_number = self.app_counter
                self.app_clients[client_number] = addr
                self.app_counter += 1
            elif device_type == "robot":
                client_number = self.robot_counter
                self.robot_clients[client_number] = addr
                self.robot_counter += 1
            else:
                device_type = "unknown"
                client_number = 0
            
            self.clients[addr] = (client_socket, device_type)
            self.add_log(f"{device_type} #{client_number} 연결됨: {addr}")
            
            # GUI 업데이트
            self.root.after(0, self.update_client_list)
            
            # 메시지 처리 루프
            while self.is_running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                message = data.decode().strip()
                self.add_log(f"{device_type} #{client_number} -> {message}")
                
                # 메시지 처리 (기존 message_handler 사용)
                # TODO: message_handler와 연동
                
        except Exception as e:
            self.add_log(f"클라이언트 {addr} 오류: {e}")
        finally:
            # 연결 정리
            if addr in self.clients:
                del self.clients[addr]
            
            # app/robot 클라이언트 목록에서 제거
            for num, client_addr in list(self.app_clients.items()):
                if client_addr == addr:
                    del self.app_clients[num]
                    break
            
            for num, client_addr in list(self.robot_clients.items()):
                if client_addr == addr:
                    del self.robot_clients[num]
                    break
            
            try:
                client_socket.close()
            except:
                pass
            
            self.add_log(f"클라이언트 {addr} 연결 해제")
            self.root.after(0, self.update_client_list)

    def update_client_list(self):
        """클라이언트 목록 업데이트"""
        # 기존 항목 삭제
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        
        # App 클라이언트 추가
        for num, addr in self.app_clients.items():
            if addr in self.clients:
                self.client_tree.insert("", "end", values=(num, "App", f"{addr[0]}:{addr[1]}", "연결됨"))
        
        # Robot 클라이언트 추가
        for num, addr in self.robot_clients.items():
            if addr in self.clients:
                self.client_tree.insert("", "end", values=(num, "Robot", f"{addr[0]}:{addr[1]}", "연결됨"))

    def update_parking_status(self):
        """주차 상태 업데이트"""
        self.parking_text.delete(1.0, tk.END)
        
        try:
            status = self.export_parking_status()
            
            if not status:
                self.parking_text.insert(tk.END, "현재 주차된 차량이 없습니다.\n")
            else:
                self.parking_text.insert(tk.END, f"총 {len(status)}대 차량이 주차되어 있습니다.\n\n")
                
                for car_number, info in status.items():
                    location = f"Sector {info['sector']} - {info['side']} - Subzone {info['subzone']} - {info['direction']}"
                    self.parking_text.insert(tk.END, f"🚗 {car_number}: {location}\n")
                    
        except Exception as e:
            self.parking_text.insert(tk.END, f"주차 상태 조회 오류: {e}\n")

    def export_parking_status(self):
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
        except Exception as e:
            self.add_log(f"주차 상태 추출 오류: {e}")
        
        return status

    def reset_all_parking(self):
        """모든 주차공간 초기화"""
        if messagebox.askyesno("확인", "모든 주차공간을 초기화하시겠습니까?"):
            try:
                for sector in find_destination.parking_lot:
                    for side in ["left", "right"]:
                        subzones = getattr(sector, side)
                        for subzone in subzones:
                            for direction in ["left", "right"]:
                                space = getattr(subzone, direction)
                                space.car_number = None
                
                self.add_log("모든 주차공간이 초기화되었습니다.")
                self.update_parking_status()
                
            except Exception as e:
                self.add_log(f"주차공간 초기화 오류: {e}")
                messagebox.showerror("오류", f"주차공간 초기화 실패: {e}")

    def send_command(self):
        """명령어 전송"""
        try:
            target = self.target_var.get()
            number = int(self.number_var.get())
            message = self.message_var.get().strip()
            
            if not message:
                messagebox.showwarning("경고", "메시지를 입력하세요.")
                return
            
            if target == "app":
                if number in self.app_clients:
                    addr = self.app_clients[number]
                    self.clients[addr][0].sendall((message + '\n').encode())
                    self.add_log(f"App #{number}에게 전송: {message}")
                else:
                    messagebox.showerror("오류", f"App #{number}이 연결되어 있지 않습니다.")
                    
            elif target == "robot":
                if number in self.robot_clients:
                    addr = self.robot_clients[number]
                    self.clients[addr][0].sendall((message + '\n').encode())
                    self.add_log(f"Robot #{number}에게 전송: {message}")
                else:
                    messagebox.showerror("오류", f"Robot #{number}이 연결되어 있지 않습니다.")
                    
            elif target == "server":
                # 서버 명령어 처리
                self.handle_server_command(message)
            
            # 메시지 입력창 클리어
            self.message_var.set("")
            
        except ValueError:
            messagebox.showerror("오류", "번호는 숫자여야 합니다.")
        except Exception as e:
            messagebox.showerror("오류", f"명령어 전송 실패: {e}")

    def quick_command(self, command):
        """빠른 명령어 실행"""
        parts = command.split(" ", 2)
        if len(parts) >= 3:
            self.target_var.set(parts[0])
            self.number_var.set(parts[1])
            self.message_var.set(parts[2])
            self.send_command()

    def handle_server_command(self, command):
        """서버 명령어 처리"""
        if command == "STATUS":
            self.update_parking_status()
            self.add_log("주차 상태 업데이트 완료")
        elif command == "LIST":
            self.update_client_list()
            self.add_log("클라이언트 목록 업데이트 완료")
        elif command == "RESET":
            self.reset_all_parking()
        else:
            self.add_log(f"알 수 없는 서버 명령어: {command}")

    def clear_logs(self):
        """로그 지우기"""
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")

    def save_logs(self):
        """로그 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"server_log_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log_text.get(1.0, tk.END))
            
            messagebox.showinfo("완료", f"로그가 저장되었습니다: {filename}")
            self.add_log(f"로그 저장 완료: {filename}")
            
        except Exception as e:
            messagebox.showerror("오류", f"로그 저장 실패: {e}")

def main():
    root = tk.Tk()
    app = ServerGUI(root)
    
    # 창 닫기 이벤트 처리
    def on_closing():
        if app.is_running:
            if messagebox.askokcancel("종료", "서버가 실행 중입니다. 종료하시겠습니까?"):
                app.stop_server()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
