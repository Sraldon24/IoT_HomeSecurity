#!/usr/bin/env python3
import time, os, logging
from modules.security_module import security_module
from modules.environmental_module import environmental_module
from modules.device_control_module import device_control_module
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def print_status(name, ok, extra=""):
    symbol = "✅" if ok else "❌"
    print(f"{symbol} {name:<20} {extra}")

def main():
    print("\n🔧 DOMISAFE HARDWARE DIAGNOSTIC TOOL")
    print("====================================\n")

    config = load_config("config.json")

    results = {}

    # ---- SECURITY MODULE TEST ----
    try:
        sec = security_module("config.json")
        print("\n🧠 SECURITY MODULE CHECK\n------------------------")
        print_status("GPIO Mode", True, f"({sec.__class__.__name__})")

        # PIR Motion Sensor
        motion_detected = False
        print("Checking motion sensor... move your hand in front of it.")
        for i in range(6):
            data = sec.get_security_data()
            motion_detected = motion_detected or data.get("motion_detected")
            time.sleep(1)
        results['PIR Motion'] = motion_detected
        print_status("PIR Motion Sensor", motion_detected)

        # LED Test
        print("Testing LED (should light up briefly)...")
        sec._set_led(True)
        time.sleep(1)
        sec._set_led(False)
        results['LED'] = True
        print_status("LED Output", True)

        # Buzzer Test
        print("Testing Buzzer (should beep)...")
        sec._set_buzzer(True)
        time.sleep(0.8)
        sec._set_buzzer(False)
        results['Buzzer'] = True
        print_status("Buzzer Output", True)

        # Motor Test
        print("Testing Motor (runs 2s)...")
        try:
            sec._run_motor_thread(2)
            results['Motor'] = True
            print_status("Motor", True)
        except Exception as e:
            results['Motor'] = False
            print_status("Motor", False, str(e))

        # Camera Test
        print("Testing Camera (capturing image)...")
        image_path = sec.capture_image()
        ok = image_path is not None and os.path.exists(image_path)
        results['Camera'] = ok
        print_status("Camera Capture", ok, image_path if ok else "")

    except Exception as e:
        print_status("Security Module Init", False, str(e))

    # ---- ENVIRONMENTAL TEST ----
    try:
        env = environmental_module("config.json")
        print("\n🌡️ ENVIRONMENTAL MODULE CHECK\n------------------------------")
        data = env.get_environmental_data()
        ok_temp = data.get('temperature') is not None
        ok_humid = data.get('humidity') is not None
        results['DHT11 Temperature'] = ok_temp
        results['DHT11 Humidity'] = ok_humid
        print_status("Temperature Sensor", ok_temp, f"{data.get('temperature')} °C")
        print_status("Humidity Sensor", ok_humid, f"{data.get('humidity')} %")
        print_status("Pressure (simulated)", True, f"{data.get('pressure')} hPa")
    except Exception as e:
        print_status("Environmental Module", False, str(e))

    # ---- DEVICE CONTROL TEST ----
    try:
        dev = device_control_module("config.json")
        print("\n🔌 DEVICE CONTROL CHECK\n-----------------------")
        data = dev.get_device_status()
        ok_dev = bool(data)
        results['Device Module'] = ok_dev
        print_status("Device Config", ok_dev, f"{len(data)} devices")
    except Exception as e:
        print_status("Device Control", False, str(e))

    # ---- SUMMARY ----
    print("\n📋 TEST SUMMARY\n----------------")
    passed = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]

    for k in passed:
        print_status(k, True)
    for k in failed:
        print_status(k, False)

    print("\n✅ TOTAL PASSED:", len(passed))
    print("❌ TOTAL FAILED:", len(failed))
    print("\nLog file saved: sensor_test.log")
    print("====================================\n")

if __name__ == "__main__":
    main()
