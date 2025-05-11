from robot_action import detect_and_dock, forward, rotate, agv_stop
from flask_client import start_client, stop_client, wait_for_signal,send_to_flask
from agv_lift import lift
import threading

def main_sequence1():
    """
    메인 작업 시퀀스1 실행.
    """
    print("Starting main task...")
    
    # Step 1: AGV 전진 3초
    forward(3)
    print("Step 1: Forward complete.")
    
    # Step 2: 시계 방향 90도 회전
    rotate("clockwise", 3)
    print("Step 2: Rotation complete.")

    # # Step 3: ArUco 마커 탐지 및 도킹
    # if detect_and_dock():
    #     print("Step 3: Marker detected and docking successful.")
    # else:
    #     print("Step 3: Marker detection or docking failed.")

    send_to_flask("hi web server, im arrive")
    
    # Step 4: 리프트 작동
    lift("UP", 2.5)
    print("Step 4: Lift operation complete.")

######################################################2#############################
def main_sequence2():
    """
    메인 작업 시퀀스2 실행.
    """
    print("Starting main task...")
    
    # Step 1: AGV 전진 3초
    forward(3)
    print("Step 1: Forward complete.")
    
    # Step 2: 시계 방향 90도 회전
    rotate("clockwise", 3)
    print("Step 2: Rotation complete.")

    # Step 3: ArUco 마커 탐지 및 도킹
    if detect_and_dock():
        print("Step 3: Marker detected and docking successful.")
    else:
        print("Step 3: Marker detection or docking failed.")

    # Step 4: 리프트 작동
    lift("UP", 2.5)
    print("Step 4: Lift operation complete.")

if __name__ == "__main__":
    try:
        # WebSocket 클라이언트를 별도 스레드에서 실행
        client_thread = threading.Thread(target=start_client, daemon=True)
        client_thread.start()

        # 서버 신호 대기
        if wait_for_signal('A', timeout=30):
            print("Signal 'A' received. Starting main sequence.")
            main_sequence1()
        elif wait_for_signal('C',timeout=60):
            print("Signal 'C' received. Starting main sequence.")
            main_sequence2()
        
        else:
            print("Timeout: Did not receive signal 'A'. Exiting.")

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # WebSocket 클라이언트 종료
        stop_client()
        agv_stop()
        print("Stopped AGV and WebSocket client.")

