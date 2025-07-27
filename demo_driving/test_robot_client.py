#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트용 가짜 로봇 클라이언트
실제 로봇 하드웨어 없이 메시지 흐름과 앱 화면 변화를 테스트하기 위한 파일
"""

import socket
import time
import threading

class TestRobotClient:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect_to_server(self):
        """서버에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.sendall(b"robot\n")  # 로봇으로 식별
            self.connected = True
            print(f"[테스트 로봇] 서버 연결 성공: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[테스트 로봇] 서버 연결 실패: {e}")
            return False
    
    def send_message(self, message):
        """서버에 메시지 전송"""
        if self.connected and self.socket:
            try:
                self.socket.sendall(f"{message}\n".encode())
                print(f"[테스트 로봇] 전송: {message}")
            except Exception as e:
                print(f"[테스트 로봇] 메시지 전송 실패: {e}")
                self.connected = False
    
    def simulate_parking_process(self, sector, side, subzone, direction, car_number):
        """입차 과정 시뮬레이션"""
        print(f"\n=== 입차 시뮬레이션 시작: {car_number} ===")
        
        # 1. 대기 위치에서 시작
        print("[1단계] 대기 위치 출발")
        self.send_message("starting_point,0,None,None")
        time.sleep(2)
        
        # 2. sector 도착
        print(f"[2단계] Sector {sector} 도착")
        self.send_message(f"sector_arrived,{sector},None,None")
        time.sleep(2)
        
        # 3. subzone 도착
        print(f"[3단계] Subzone {side}-{subzone} 도착")
        self.send_message(f"subzone_arrived,{sector},{side},{subzone}")
        time.sleep(2)
        
        # 4. 주차 완료
        print("[4단계] 주차 완료")
        self.send_message(f"DONE,{sector},{side},{subzone},{direction},{car_number}")
        time.sleep(2)
        
        # 5. 복귀 과정 시뮬레이션
        print("[5단계] 복귀 시작")
        self.send_message(f"subzone_arrived,{sector},{side},{subzone}")
        time.sleep(1)
        
        self.send_message(f"sector_arrived,{sector},None,None")
        time.sleep(1)
        
        self.send_message("starting_point,0,None,None")
        time.sleep(1)
        
        # 6. 전체 작업 완료
        print("[6단계] 작업 완료")
        self.send_message("COMPLETE")
        
        print(f"=== 입차 시뮬레이션 완료: {car_number} ===\n")
    
    def simulate_exit_process(self, sector, side, subzone, direction, car_number):
        """출차 과정 시뮬레이션"""
        print(f"\n=== 출차 시뮬레이션 시작: {car_number} ===")
        
        # 1. 대기 위치에서 시작
        print("[1단계] 대기 위치 출발")
        self.send_message("starting_point,0,None,None")
        time.sleep(2)
        
        # 2. sector 도착
        print(f"[2단계] Sector {sector} 도착")
        self.send_message(f"sector_arrived,{sector},None,None")
        time.sleep(2)
        
        # 3. subzone 도착
        print(f"[3단계] Subzone {side}-{subzone} 도착")
        self.send_message(f"subzone_arrived,{sector},{side},{subzone}")
        time.sleep(2)
        
        # 4. 출차 완료
        print("[4단계] 출차 완료")
        self.send_message(f"OUT_DONE,{sector},{side},{subzone},{direction},{car_number}")
        time.sleep(2)
        
        # 5. 복귀 과정 시뮬레이션
        print("[5단계] 복귀 시작")
        self.send_message(f"subzone_arrived,{sector},{side},{subzone}")
        time.sleep(1)
        
        self.send_message(f"sector_arrived,{sector},None,None")
        time.sleep(1)
        
        self.send_message("starting_point,0,None,None")
        time.sleep(1)
        
        # 6. 전체 작업 완료
        print("[6단계] 작업 완료")
        self.send_message("COMPLETE")
        
        print(f"=== 출차 시뮬레이션 완료: {car_number} ===\n")
    
    def listen_for_commands(self):
        """서버로부터 명령 수신"""
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                command = data.decode().strip()
                print(f"[테스트 로봇] 수신: {command}")
                
                # 명령 처리
                if command.startswith("PARK"):
                    # PARK,1,left,1,left,1234
                    parts = command.split(",")
                    if len(parts) >= 6:
                        _, sector, side, subzone, direction, car_number = parts
                        print(f"[테스트 로봇] 입차 명령 받음: {car_number}")
                        # 별도 스레드에서 시뮬레이션 실행
                        threading.Thread(
                            target=self.simulate_parking_process,
                            args=(sector, side, subzone, direction, car_number),
                            daemon=True
                        ).start()
                
                elif command.startswith("OUT"):
                    # OUT,1,left,1,left,1234
                    parts = command.split(",")
                    if len(parts) >= 6:
                        _, sector, side, subzone, direction, car_number = parts
                        print(f"[테스트 로봇] 출차 명령 받음: {car_number}")
                        # 별도 스레드에서 시뮬레이션 실행
                        threading.Thread(
                            target=self.simulate_exit_process,
                            args=(sector, side, subzone, direction, car_number),
                            daemon=True
                        ).start()
                
            except Exception as e:
                print(f"[테스트 로봇] 명령 수신 오류: {e}")
                break
    
    def start(self):
        """테스트 로봇 시작"""
        if self.connect_to_server():
            # 명령 수신 스레드 시작
            listen_thread = threading.Thread(target=self.listen_for_commands, daemon=True)
            listen_thread.start()
            
            print("\n테스트 로봇이 시작되었습니다!")
            print("서버에서 입차/출차 명령을 보내면 자동으로 시뮬레이션됩니다.")
            print("종료하려면 Ctrl+C를 누르세요.\n")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[테스트 로봇] 종료 중...")
                self.connected = False
                if self.socket:
                    self.socket.close()
                print("[테스트 로봇] 종료 완료")
        else:
            print("[테스트 로봇] 서버 연결 실패로 종료합니다.")

def main():
    print("=== 테스트용 로봇 클라이언트 ===")
    print("실제 로봇 하드웨어 없이 메시지 흐름을 테스트합니다.")
    print()
    
    # 서버 정보 입력
    host = input("서버 IP (기본값: 127.0.0.1): ").strip() or "127.0.0.1"
    port_input = input("서버 포트 (기본값: 12345): ").strip()
    port = int(port_input) if port_input else 12345
    
    # 테스트 로봇 시작
    test_robot = TestRobotClient(host, port)
    test_robot.start()

if __name__ == "__main__":
    main()
