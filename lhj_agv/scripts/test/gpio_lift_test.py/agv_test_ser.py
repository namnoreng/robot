import socketio

# Flask 서버 URL
server_url = "http://172.30.1.71:5000/agv_data"

# WebSocket 클라이언트 설정
sio = socketio.Client()

# 전역 변수
response_value = None  # 서버로부터 받은 응답 저장

@sio.on('connect')
def on_connect():
    """서버 연결 성공 시 호출"""
    print("서버에 연결되었습니다.")

@sio.on('disconnect')
def on_disconnect():
    """서버 연결 종료 시 호출"""
    print("서버와의 연결이 종료되었습니다.")

@sio.on('agv_response')
def on_agv_response(data):
    """서버로부터 'agv_response' 이벤트 수신 시 호출"""
    global response_value
    response_value = data.get('response')
    print(f"서버로부터 수신한 데이터: {response_value}")

# WebSocket 클라이언트 실행
if __name__ == "__main__":
    try:
        # 서버 연결
        print(f"{server_url}에 연결 시도 중...")
        sio.connect(server_url)

        # 이벤트 대기
        print("이벤트 대기 중...")
        sio.wait()
    except Exception as e:
        print(f"오류 발생: {e}")
