#!/usr/bin/env python3
import time, logging
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
    print("\n⚙️  SINGLE-DIRECTION MOTOR TEST")
    print("===============================")

    cfg = load_config("config.json")
    pos_pin = int(cfg.get("MOTOR_POS_PIN", 20))
    neg_pin = int(cfg.get("MOTOR_NEG_PIN", 21))
    print(f"Using GPIO {pos_pin} (POS) and {neg_pin} (NEG) | mode={GPIO_MODE}")

    if GPIO_MODE == "adafruit":
        pos = digitalio.DigitalInOut(getattr(board, f"D{pos_pin}"))
        neg = digitalio.DigitalInOut(getattr(board, f"D{neg_pin}"))
        pos.direction = digitalio.Direction.OUTPUT
        neg.direction = digitalio.Direction.OUTPUT

        def on():
            pos.value = True
            neg.value = False
            logger.info("➡️  Motor ON (POS=1, NEG=0)")

        def off():
            pos.value = False
            neg.value = False
            logger.info("⏹️  Motor OFF (POS=0, NEG=0)")
    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pos_pin, GPIO.OUT)
        GPIO.setup(neg_pin, GPIO.OUT)

        def on():
            GPIO.output(pos_pin, True)
            GPIO.output(neg_pin, False)
            logger.info("➡️  Motor ON (POS=1, NEG=0)")

        def off():
            GPIO.output(pos_pin, False)
            GPIO.output(neg_pin, False)
            logger.info("⏹️  Motor OFF (POS=0, NEG=0)")

    try:
        print("Turning motor ON for 2 seconds...")
        on()
        time.sleep(2)
        off()
        if GPIO_MODE != "adafruit":
            GPIO.cleanup()
        print("✅ Test complete. If motor didn’t spin:")
        print("   • Check driver’s EN/ENA pin is HIGH or jumper present")
        print("   • Verify external motor power (≥ 5 V / 9–12 V)")
        print("   • Confirm driver GND and Pi GND are connected\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        if GPIO_MODE != "adafruit":
            GPIO.cleanup()

if __name__ == "__main__":
    main()
