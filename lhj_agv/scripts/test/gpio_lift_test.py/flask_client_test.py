import requests
import RPi.GPIO as GPIO
import time

# Flask 서버 URL
server_url = "http://172.30.1.71:5000/data"

# GPIO 핀 설정
GPIO.setmode(GPIO.BCM)  # GPIO 핀 번호 설정 (BCM 모드)
GPIO.setwarnings(False)

# 핀 설정
DIR_PIN = 11       # 방향 제어 핀
STEP_PIN = 7       # 스텝 제어 핀

# GPIO 초기화
GPIO.setup(DIR_PIN, GPIO.OUT)
GPIO.setup(STEP_PIN, GPIO.OUT)

# AGV 데이터를 Flask 서버로 전송
def send_to_flask(agv_status):
    data_to_send = {
        "agv": {
            "status": agv_status
        }
    }
    try:
        response = requests.post(server_url, json=data_to_send)
        if response.status_code == 200:
            print("Response from server:", response.json())
            return response.json().get('response')
        else:
            print(f"Error: Received status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to Flask: {e}")
        return None

def lift(direction, duration):
    """
    스텝 모터를 지정된 방향으로 지정된 시간 동안 제어합니다.
    :param direction: "UP" 또는 "DOWN"
    :param duration: 동작 시간 (초 단위)
    """
    GPIO.output(DIR_PIN, GPIO.HIGH if direction == "UP" else GPIO.LOW)
    print(f"리프트 {direction} 시작...")

    start_time = time.time()
    while time.time() - start_time < duration:
        GPIO.output(STEP_PIN, GPIO.HIGH)
        time.sleep(0.001)  # STEP 신호 ON 시간 (1ms)
        GPIO.output(STEP_PIN, GPIO.LOW)
        time.sleep(0.001)  # STEP 신호 OFF 시간 (1ms)

    print(f"리프트 {direction} 완료.")

if __name__ == "__main__":
    try:
        # 데이터 입력 루프
        while True:
            user_input = input("데이터를 입력하세요 (A, G, V, q: 종료): ")

            if user_input == 'A':
                # 스텝 모터를 올리는 동작 (예: 2.5초 동안)
                lift("UP", 2.5)
                response_value = send_to_flask("식당 도착")
            elif user_input == 'G':
                # 스텝 모터를 내리는 동작 (예: 2.5초 동안)
                lift("DOWN", 2.5)
                response_value = send_to_flask("환자한테 출발")
            elif user_input == 'V':
                # AGV의 차고지 도착 상태 전송
                response_value = send_to_flask("차고지 도착")
            elif user_input == 'q':
                print("프로그램 종료")
                break
            else:
                print("Invalid input. Try again.")
                continue

            # 서버로부터 받은 응답 처리
            if response_value == 'X':
                print("hello agv")

    except KeyboardInterrupt:
        print("\n프로그램 중단")
    finally:
        # GPIO 리소스 해제
        GPIO.cleanup()
