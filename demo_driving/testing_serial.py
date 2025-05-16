import serial

serial_server = serial.Serial("COM10",115200)  # 시리얼 포트와 보드레이트 설정

while True:
    mode = input("모드 입력: ")

    if mode == "1":
        serial_server.write('1'.encode())  # STM32에 메시지 전송
        print("모드 1 전송")

    elif mode == "2":
        serial_server.write('2'.encode())
        print("모드 2 전송")

    elif mode == "3":
        serial_server.write('3'.encode())
        print("모드 3 전송")
        stm_message = serial_server.read_until(b'\n')  # STM32에서 오는 메시지 수신
        print(stm_message.decode().strip())  # 수신한 메시지 출력

    elif mode == "4":
        serial_server.write('4'.encode())
        print("모드 4 전송")
        stm_message = serial_server.read_until(b'\n')  # STM32에서 오는 메시지 수신
        print(stm_message.decode().strip())
        
    elif mode == "9":
        serial_server.write('9'.encode())
        print("모드 9 전송")

    