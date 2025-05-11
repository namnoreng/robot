import RPi.GPIO as GPIO
import time
from setting import GPIO_DIR_PIN, GPIO_STEP_PIN

GPIO.setwarnings(False)
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_DIR_PIN, GPIO.OUT)
GPIO.setup(GPIO_STEP_PIN, GPIO.OUT)

def lift(direction, duration):
    GPIO.output(GPIO_DIR_PIN, GPIO.HIGH if direction == "UP" else GPIO.LOW)
    print(f"Lifting {direction} for {duration} seconds...")
    start_time = time.time()
    while time.time() - start_time < duration:
        GPIO.output(GPIO_STEP_PIN, GPIO.HIGH)
        time.sleep(0.001)
        GPIO.output(GPIO_STEP_PIN, GPIO.LOW)
        time.sleep(0.001)
    print(f"Lifting {direction} completed.")
