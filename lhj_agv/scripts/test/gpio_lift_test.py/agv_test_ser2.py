import requests
import socketio

# Flask 서버 URL
server_url = "http://172.30.1.71:5000/agv_data"

# WebSocket 클라이언트 설정
sio = socketio.Client()

# 변수 선언
response_value = None  # 서버 응답 값을 저장할 변수


@sio.on('connect')
def on_connect():
    print("Connected to the server")


@sio.on('disconnect')
def on_disconnect():
    print("Disconnected from the server")


@sio.on('agv_response')
def on_agv_response(data):
    global response_value
    # 서버 응답에서 'response' 값만 추출
    response_value = data.get('response')
    print(response_value)  # 'response' 값만 출력

    # 조건문 처리
    if response_value == 'X':
        print("hello agv")


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
        else:
            print(f"Error: Received status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to Flask: {e}")


if __name__ == "__main__":
    # WebSocket 서버 연결
    sio.connect("http://172.30.1.71:5000")

    # 데이터 입력 루프
    while True:
        user_input = input("데이터를 입력하세요 (A, G, V): ")
        if user_input == 'A':
            send_to_flask("식당 도착")
        elif user_input == 'G':
            send_to_flask("환자한테 출발")
        elif user_input == 'V':
            send_to_flask("차고지 도착")
        else:
            print("Invalid input. Try again.")
