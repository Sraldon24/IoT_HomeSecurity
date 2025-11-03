#!/usr/bin/env python3
import time, logging, os
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

try:
    import board, digitalio
    GPIO_MODE = "adafruit"
except Exception:
    import RPi.GPIO as GPIO
    GPIO_MODE = "rpi"

def main():
    print("\n🧠 DOMISAFE MOTOR TEST")
    print("========================\n")

    cfg = load_config("config.json")
    pos_pin = int(cfg.get("MOTOR_POS_PIN", 20))
    neg_pin = int(cfg.get("MOTOR_NEG_PIN", 21))
    print(f"Configured pins: POS={pos_pin}, NEG={neg_pin} (mode={GPIO_MODE})")

    if GPIO_MODE == "adafruit":
        pos = digitalio.DigitalInOut(getattr(board, f"D{pos_pin}"))
        neg = digitalio.DigitalInOut(getattr(board, f"D{neg_pin}"))
        pos.direction = digitalio.Direction.OUTPUT
        neg.direction = digitalio.Direction.OUTPUT

        def motor_forward():
            pos.value = True
            neg.value = False
            logger.info("⚙️ Motor FORWARD (POS=1, NEG=0)")

        def motor_backward():
            pos.value = False
            neg.value = True
            logger.info("⚙️ Motor REVERSE (POS=0, NEG=1)")

        def motor_stop():
            pos.value = False
            neg.value = False
            logger.info("⛔ Motor STOPPED (POS=0, NEG=0)")

    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pos_pin, GPIO.OUT)
        GPIO.setup(neg_pin, GPIO.OUT)

        def motor_forward():
            GPIO.output(pos_pin, True)
            GPIO.output(neg_pin, False)
            logger.info("⚙️ Motor FORWARD (POS=1, NEG=0)")

        def motor_backward():
            GPIO.output(pos_pin, False)
            GPIO.output(neg_pin, True)
            logger.info("⚙️ Motor REVERSE (POS=0, NEG=1)")

        def motor_stop():
            GPIO.output(pos_pin, False)
            GPIO.output(neg_pin, False)
            logger.info("⛔ Motor STOPPED (POS=0, NEG=0)")

    try:
        print("\nRunning forward test...")
        motor_forward()
        time.sleep(2)
        motor_stop()
        time.sleep(1)

        print("\nRunning reverse test...")
        motor_backward()
        time.sleep(2)
        motor_stop()

        print("\n✅ Motor test sequence complete.")
        print("If nothing moved, check your motor driver wiring:")
        print("   → POS (GPIO 20) to IN1, NEG (GPIO 21) to IN2")
        print("   → Enable pin (if present) should be HIGH")
        print("   → Motor powered separately with external supply\n")

    finally:
        if GPIO_MODE != "adafruit":
            GPIO.cleanup()

if __name__ == "__main__":
    main()
