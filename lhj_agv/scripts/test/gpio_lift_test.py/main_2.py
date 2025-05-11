from action2 import detect_and_dock,detect_and_dock_with_distance, forward, retreat, rotate, pan_left, pan_right, agv_stop, align_to_marker
from flask_client import send_data, receive_data
from gpio_control import set_gpio_high
from setting import GPIO_PIN
# detect_marker_and_rotate
if __name__ == "__main__":
    print("작업 시작...")

    # 1. 전진 3초
    forward(3)

    # 2. 90도 회전
    rotate("clockwise", 3)

    if detect_and_dock():
        print("ID 2 도킹 성공")
        
    else:
        print("ID 2 도킹 실패")

    forward(1)
    # 3. ID 2 마커 탐지 및 도킹
    #
    #send_data("A")  # 4. Flask 서버로 데이터 전송

    # 5. GPIO 7번 HIGH
    #set_gpio_high(GPIO_PIN)

    # 6. Flask 서버에서 데이터 수신
    #received = receive_data()
    #if received == "B":
    #    print("Flask 서버로부터 데이터 B 수신.")
    
    # 7. 후진 1초
    retreat(1)

    # 8. 왼쪽 이동 1초
    pan_left(2)

    # 9. 전진 
    forward(4)
    agv_stop()
    

    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 3 ")
    else:
        print("ID 3 ")

    #11. 90도 회전
    rotate("counter_clockwise", 3)

    # 12. 전진 
    forward(3)
    agv_stop()

    if detect_and_dock_with_distance(stop_distance=0.5):
        print("ID 4")
    else:
        print("ID 4")

    # 13. 90도 회전
    rotate("counter_clockwise", 3)

    # 14. 전진 
    forward(3)
    agv_stop()

    
    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 5")
    else:
        print("ID 5")
    
    retreat(1)

    # 15. 90도 회전
    rotate("clockwise", 3)

    # 16. 전진 
    forward(2)
    agv_stop()



    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 6")
    else:
        print("ID 6")

    #pan_right(0.5)

    # 17. 90도 회전
    rotate("counter_clockwise", 3)

    if detect_and_dock():
        print("ID 7 도킹 성공")
        
    else:
        print("ID 7 도킹 실패")

    forward(1)
    # 7. 후진 1초
    retreat(1.3)

    # 17. 90도 회전
    rotate("counter_clockwise", 3)

    # 16. 전진 
    forward(3)
    agv_stop()
    
    forward(3)
    agv_stop()

    pan_left(1)

 
    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 8")
    else:
        print("ID 8")

    pan_right(2)

    # 16. 전진 
    forward(3)

    if detect_and_dock_with_distance(stop_distance=0.3):
        print("ID 9")
    else:
        print("ID 9")

    # 15. 180도 회전
    rotate("clockwise", 3)
    agv_stop()
    rotate("clockwise", 3)
    agv_stop()
    retreat(1)
    # # 10~22. 다양한 작업 수행
    # marker_actions = [
    #     {"id": 3, "distance": 0.1, "rotate_dir": "counter_clockwise", "rotate_time": 3},
    #     {"id": 4, "distance": 0.2, "rotate_dir": "counter_clockwise", "rotate_time": 3},
    #     {"id": 5, "distance": 0.1, "rotate_dir": "clockwise", "rotate_time": 3},
    #     {"id": 6, "distance": 0.1, "rotate_dir": "counter_clockwise", "rotate_time": 3}
    # ]

    # for action in marker_actions:
    #     if detect_marker_and_rotate(
    #         marker_id=action["id"],
    #         stop_distance=action["distance"],
    #         rotate_duration=action["rotate_time"],
    #         rotate_direction=action["rotate_dir"]
    #     ):
    #         print(f"ID {action['id']}에서 {action['rotate_dir']} 방향 회전 완료.")
    #         forward(2)
    #     else:
    #         print(f"ID {action['id']} 탐지 실패. 다음 단계로 진행.")

    print("작업 완료.")
