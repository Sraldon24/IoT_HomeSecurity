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
    print("\n⚙️  SINGLE-PIN MOTOR TEST")
    print("===============================")

    cfg = load_config("config.json")
    # Use a single control pin for the motor driver (ENA/IN1, etc.)
    motor_pin = int(cfg.get("MOTOR_PIN", cfg.get("MOTOR_POS_PIN", 20)))
    print(f"Using GPIO {motor_pin} (SINGLE CONTROL) | mode={GPIO_MODE}")

    if GPIO_MODE == "adafruit":
        pin = digitalio.DigitalInOut(getattr(board, f"D{motor_pin}"))
        pin.direction = digitalio.Direction.OUTPUT

        def on():
            pin.value = True
            logger.info("➡️  Motor ON (PIN=1)")

        def off():
            pin.value = False
            logger.info("⏹️  Motor OFF (PIN=0)")
    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(motor_pin, GPIO.OUT)

        def on():
            GPIO.output(motor_pin, True)
            logger.info("➡️  Motor ON (PIN=1)")

        def off():
            GPIO.output(motor_pin, False)
            logger.info("⏹️  Motor OFF (PIN=0)")

    try:
        print("Turning motor ON for 3 seconds...")
        on()
        time.sleep(3)
        off()
        if GPIO_MODE != "adafruit":
            GPIO.cleanup()
        print("✅ Test complete. If motor didn’t spin:")
        print("   • Ensure driver EN/ENA (or equivalent) is connected to this control pin and pulled HIGH to enable motor")
        print("   • Verify external motor power and common ground")
        print("   • If using an H-bridge, the direction pins may still be required depending on wiring\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        if GPIO_MODE != "adafruit":
            GPIO.cleanup()

if __name__ == "__main__":
    main()
