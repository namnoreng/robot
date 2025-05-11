from robot_action import detect_and_dock, forward, rotate, agv_stop,retreat, pan_left, pan_right, detect_and_dock_with_distance
from flask_client import start_client, stop_client, wait_for_signal, send_to_flask
from agv_lift import lift
import threading
import time

# 전역 변수 및 동기화 조건
current_signal = None
signal_condition = threading.Condition()

def main_sequence1():
    """
    메인 작업 시퀀스 1 실행.
    """
    print("Starting Main Task 1...")
    send_to_flask("준호야 밥먹자")
    
    # Step 1: AGV 전진 3초
    forward(3)
    # Step 2: 시계 방향 90도 회전
    rotate("clockwise", 3)
    
    if detect_and_dock():
        print("ID 2 도킹 성공")
    else:
        print("ID 2 도킹 실패")

    # 서버로 메시지 전송
    send_to_flask("식당 도착")
    print("")

    forward(1)
    
    # Step 4: 리프트 작동
    lift("UP", 2.5)
    ##robot arm move!!!

    lift("DOWN", 2.5)
    
    retreat(1)

    pan_left(2)

    forward(4)
    agv_stop()

    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 3 ")
    else:
        print("ID 3 ")

    rotate("counter_clockwise", 3)

    forward(3)
    agv_stop()

    if detect_and_dock_with_distance(stop_distance=0.5):
        print("ID 4")
    else:
        print("ID 4")

    rotate("counter_clockwise", 3)

    forward(3)
    agv_stop()

    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 5")
    else:
        print("ID 5")
    
    retreat(1)

    # right 90도 회전
    rotate("clockwise", 3)

    # 전진 
    forward(2)
    agv_stop()

    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 6")
    else:
        print("ID 6")


    # left 90도 회전
    rotate("counter_clockwise", 3)

    if detect_and_dock():
        print("ID 7 도킹 성공")
        
    else:
        print("ID 7 도킹 실패")
    
    forward(1)

    # 서버로 메시지 전송
    send_to_flask("patient")
    print("")

    forward(1)
    
    # Step 4: 리프트 작동
    lift("UP", 2.5)
    ##robot arm move!!!
    #lift("DOWN", 2.5)


def main_sequence2():
    """
    메인 작업 시퀀스 2 실행.
    """
    send_to_flask("come back home")
    retreat(1.3)

    rotate("counter_clockwise", 3)

    forward(3)
    agv_stop()
    pan_left(1)
    forward(3)
    agv_stop()


    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 8")
    else:
        print("ID 8")

    pan_right(2.2)

    # last 전진 
    forward(3)

    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 9")
    else:
        print("ID 9")

    # 180도 회전
    rotate("clockwise", 3)
    agv_stop()
    rotate("clockwise", 3)
    agv_stop()
    retreat(1)
    send_to_flask("5.5 team")

if __name__ == "__main__":
    try:
        # WebSocket 클라이언트를 별도 스레드에서 실행
        client_thread = threading.Thread(target=start_client, daemon=True)
        client_thread.start()

        # Step 1: Signal A 수신 후 Main Sequence 1 실행
        print("Waiting for signal 'A' to start...")
        if wait_for_signal('A', timeout=60):
            print("Signal 'A' received. Starting Main Sequence 1.")
            main_sequence1()
        else:
            print("Timeout waiting for signal 'A'. Exiting.")

        # Step 2: Signal C 수신 대기 후 Main Sequence 2 실행
        print("Waiting for signal 'C' to continue...")
        if wait_for_signal('C', timeout=600):
            print("Signal 'C' received. Starting Main Sequence 2.")
            main_sequence2()
        else:
            print("Timeout waiting for signal 'C'. Exiting.")

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # WebSocket 클라이언트 종료
        stop_client()
        agv_stop()
        print("Stopped AGV and WebSocket client.")
