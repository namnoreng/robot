import requests
import RPi.GPIO as GPIO
import time

# Flask 서버의 URL 설정
server_url = "http://172.30.1.50:5000/data"  # 변경 금지

# GPIO 핀 설정
GPIO.setmode(GPIO.BCM)  # GPIO 핀 번호 설정 (BCM 모드)
GPIO.setwarnings(False)

# 핀 설정
DIR_PIN = 11       # 방향 제어 핀
STEP_PIN = 7       # 스텝 제어 핀

# GPIO 초기화
GPIO.setup(DIR_PIN, GPIO.OUT)
GPIO.setup(STEP_PIN, GPIO.OUT)

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

def read_from_AGV():
    """
    AGV 상태를 읽어오는 함수. GPIO 핀 상태를 읽어서 AGV 명령을 반환합니다.
    :return: 'A', 'G', 또는 None
    """
    # Replace STEP_PIN with the appropriate pin configured as input
    # Placeholder logic for AGV data reading
    return None  # No signal detected (update with actual input pin)

def get_data_from_server():
    """
    Flask 서버로부터 데이터를 가져옵니다.
    :return: 서버에서 받은 'status' 데이터
    """
    try:
        response = requests.get(server_url)
        if response.status_code == 200:
            data = response.json()
            print("서버에서 받은 데이터:", data)
            return data.get("status")
        else:
            print(f"서버 응답 오류: 상태 코드 {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"서버 연결 오류: {e}")
        return None

def process_message(data):
    """
    AGV 데이터를 처리하고 Flask 서버로 전송합니다.
    :param data: AGV 상태 데이터
    """
    if data == 'A':
        print("A: 식당 도착")
        send_to_flask("식당 도착")
    elif data == 'G':
        print("G: 환자한테 출발")
        send_to_flask("환자한테 출발")
    elif data == 'V':
        print("V: 차고지 도착")
        send_to_flask("차고지 도착")
    else:
        print("알 수 없는 데이터:", data)

def send_to_flask(status):
    """
    Flask 서버로 데이터를 전송합니다.
    :param status: 전송할 상태 메시지
    """
    data_to_send = {
        "AGV": {"status": status},
    }
    try:
        response = requests.post(server_url, json=data_to_send)
        if response.status_code == 200:
            print("서버 응답:", response.json())
        else:
            print(f"서버 응답 오류: 상태 코드 {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Flask 전송 오류: {e}")

if __name__ == "__main__":
    try:
        print("프로그램 시작: 'A'(올리기), 'G'(내리기), 'q'(종료)를 입력하세요.")
        while True:
            command = input("입력: ").strip()
            if command == "A":
                lift("UP", 0.5)
            elif command == "G":
                lift("DOWN", 0.5)
            elif command == "q":
                print("프로그램 종료")
                break
            else:
                print("잘못된 입력입니다. 'A', 'G', 또는 'q'를 입력하세요.")
    except KeyboardInterrupt:
        print("\n프로그램 중단")
    finally:
        GPIO.cleanup()
