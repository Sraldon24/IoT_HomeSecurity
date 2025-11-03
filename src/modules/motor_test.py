import time, RPi.GPIO as GPIO, json

with open("../../config.json") as f:
    cfg = json.load(f)
pin = cfg.get("MOTOR_PIN", 21)

print(f"Testing motor on GPIO{pin}")
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin, GPIO.OUT)

GPIO.output(pin, GPIO.HIGH)
print("Motor ON for 3s")
time.sleep(3)
GPIO.output(pin, GPIO.LOW)
print("Motor OFF")

GPIO.cleanup(pin)

    