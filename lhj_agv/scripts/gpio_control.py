import RPi.GPIO as GPIO
import time

def set_gpio_high(pin):
    """GPIO 핀 HIGH 상태로 설정"""
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    print(f"GPIO {pin}번 HIGH 상태로 설정.")
    time.sleep(1)
    GPIO.cleanup()
