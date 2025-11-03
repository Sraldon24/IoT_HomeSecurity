#!/usr/bin/env python3
import time, logging
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Try to load GPIO libs
try:
    import board, digitalio
    GPIO_MODE = "adafruit"
except Exception:
    import RPi.GPIO as GPIO
    GPIO_MODE = "rpi"

def test_dht():
    print("\n🌡️  DHT11 SENSOR TEST")
    print("=======================")
    try:
        import adafruit_dht
        dht = adafruit_dht.DHT11(board.D4, use_pulseio=False)
        for i in range(10):
            try:
                t = dht.temperature
                h = dht.humidity
                if t is not None and h is not None:
                    print(f"✅ Read {i+1}: {t:.1f} °C  |  {h:.1f} %")
                    return True
                else:
                    print(f"⚠️  Read {i+1}: No valid data")
            except Exception as e:
                print(f"⚠️  Read {i+1} failed: {e}")
            time.sleep(2)
        print("❌ DHT11 did not respond after 10 tries.")
        return False
    except Exception as e:
        print(f"❌ Could not initialize DHT11: {e}")
        return False

def test_motor():
    print("\n⚙️  MOTOR DRIVER TEST")
    print("=====================")
    cfg = load_config("config.json")
    pos_pin = int(cfg.get("MOTOR_POS_PIN", 20))
    neg_pin = int(cfg.get("MOTOR_NEG_PIN", 21))
    print(f"Using GPIO {pos_pin} (POS) and {neg_pin} (NEG) | mode={GPIO_MODE}")

    if GPIO_MODE == "adafruit":
        pos = digitalio.DigitalInOut(getattr(board, f"D{pos_pin}"))
        neg = digitalio.DigitalInOut(getattr(board, f"D{neg_pin}"))
        pos.direction = digitalio.Direction.OUTPUT
        neg.direction = digitalio.Direction.OUTPUT

        def set_motor(fwd, rev):
            pos.value = fwd
            neg.value = rev
            logger.info(f"POS={int(fwd)}  NEG={int(rev)}")

    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pos_pin, GPIO.OUT)
        GPIO.setup(neg_pin, GPIO.OUT)
        def set_motor(fwd, rev):
            GPIO.output(pos_pin, fwd)
            GPIO.output(neg_pin, rev)
            logger.info(f"POS={int(fwd)}  NEG={int(rev)}")

    try:
        print("➡️  Forward spin (2s)...")
        set_motor(True, False)
        time.sleep(2)

        print("⏹️  Stop (1s)...")
        set_motor(False, False)
        time.sleep(1)

        print("⬅️  Reverse spin (2s)...")
        set_motor(False, True)
        time.sleep(2)

        print("⏹️  Stop.")
        set_motor(False, False)
        if GPIO_MODE != "adafruit":
            GPIO.cleanup()
        print("✅ Motor GPIO toggled successfully.")
        print("If motor didn’t move, verify:")
        print("  • Driver has external power (e.g., 9–12 V)")
        print("  • EN pin is HIGH / jumper present")
        print("  • GND shared with Pi")
        return True
    except Exception as e:
        print(f"❌ Motor test error: {e}")
        if GPIO_MODE != "adafruit":
            GPIO.cleanup()
        return False

def main():
    print("\n🧠 HARDWARE DIAGNOSTIC (DHT + MOTOR)\n====================================")
    dht_ok = test_dht()
    motor_ok = test_motor()
    print("\n📋 SUMMARY")
    print("==========")
    print(f"{'✅' if dht_ok else '❌'} DHT11 Sensor")
    print(f"{'✅' if motor_ok else '❌'} Motor / Driver Output")
    print("\nDone.\n")

if __name__ == "__main__":
    main()
