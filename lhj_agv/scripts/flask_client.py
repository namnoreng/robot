import requests
import socketio
from setting import server_url
import threading

sio = socketio.Client()
response_value = None  # 서버 응답 값을 저장하는 전역 변수
signal_condition = threading.Condition()  # 동기화를 위한 조건 객체

@sio.on('connect')
def on_connect():
    print("Connected to the server.")

@sio.on('disconnect')
def on_disconnect():
    print("Disconnected from the server.")

@sio.on('agv_response')
def on_agv_response(data):
    """서버로부터 'agv_response' 이벤트 수신 시 호출"""
    global response_value
    with signal_condition:
        response_value = data.get('response')
        print(f"Received response: {response_value}")
        signal_condition.notify_all()  # 신호를 기다리는 스레드에 알림

def wait_for_signal(target_value, timeout=30):
    """
    특정 신호를 기다립니다.
    :param target_value: 기다릴 신호 값
    :param timeout: 대기 시간 (초 단위)
    :return: True(신호 수신) 또는 False(타임아웃)
    """
    global response_value
    with signal_condition:
        signal_condition.wait_for(lambda: response_value == target_value, timeout=timeout)
        if response_value == target_value:
            return True
        return False  # 타임아웃 발생

def send_to_flask(agv_status):
    """
    AGV 데이터를 Flask 서버로 전송
    """
    data_to_send = {
        "agv": {
            "status": agv_status
        }
    }
    try:
        response = requests.post(server_url, json=data_to_send)
        if response.status_code == 200:
            print(f"Response from server: {response.json()}")
        else:
            print(f"Error: Received status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to Flask: {e}")

def start_client():
    """
    WebSocket 클라이언트를 시작하여 데이터를 지속적으로 수신합니다.
    """
    try:
        print(f"Attempting to connect to {server_url}...")
        sio.connect("http://172.30.1.71:5000")
        sio.wait()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        sio.disconnect()

def stop_client():
    """
    WebSocket 클라이언트를 안전하게 종료합니다.
    """
    sio.disconnect()
    print("Stopping WebSocket client.")
