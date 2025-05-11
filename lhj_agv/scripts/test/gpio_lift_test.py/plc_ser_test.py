import requests
import serial
import time
# Flask 서버의 URL 설정 (데이터를 처리하는 라우트로 변경)
server_url = "http://172.30.1.71:5000/plc_data"
# PLC에서 데이터를 읽는 함수
def read_from_plc(port='COM7', baudrate=115200, timeout=1):  # Windows에서 COM4 사용
    try:
        # 시리얼 포트 연결
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Connected to {port} at {baudrate} baud.")
        time.sleep(2)  # 연결 안정화 대기
        # 무한 루프 시작ㅏ
        while True:
            if ser.in_waiting > 0:  # 수신 대기 중인 데이터가 있으면
                data = ser.read()  # 바이트 단위로 데이터 수신
                hex_data = data.hex().upper()  # 16진수 문자열로 변환
                process_message(hex_data)  # 수신한 데이터 처리
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    except PermissionError:
        print(f"Permission Error: Could not access {port}. Check if another program is using it or if you have permission.")
    except KeyboardInterrupt:
        print("Program interrupted by user.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()  # 시리얼 포트 닫기
            print("Serial port closed.")
# 수신된 메시지를 처리
def process_message(data):
    if data == '01':  # HEXA 01에 대한 처리
        print("1")
        send_to_flask("음식 준비 완료")  # 첫 번째 매개변수 추가
    elif data == '02':  # 추가적인 데이터 처리 예시
        print("2")
        send_to_flask("AGV 도착 확인")  # 두 번째 매개변수 추가
    elif data == '03':  # 추가적인 데이터 처리 예시
        print("3")
        send_to_flask("컨베이어 작동")  # 세 번째 매개변수 추가
# Flask 서버로 데이터 전송
def send_to_flask(status):
    # PLC 데이터만 포함
    data_to_send = {
        "plc": {
            "status": status
        }
    }
    try:
        response = requests.post(server_url, json=data_to_send)
        if response.status_code == 200:
            print("Response from server:", response.json())
        elif response.status_code == 500:
            print("Error: Internal Server Error from server:", response.json())
        else:
            print(f"Error: Received status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to Flask: {e}")
# 메인 루프
if __name__ == "__main__":
    #read_from_plc()
   while True:
      user_input = input("데이터를 입력하세요 (01 또는 02 또는 03): ")  # 사용자 입력
      process_message(user_input)  # 입력된 데이터 처리