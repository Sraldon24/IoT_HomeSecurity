import logging, os, time
from datetime import datetime
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Try hardware modes ---
try:
    import board, digitalio
    from picamera2 import Picamera2
    import cv2
    GPIO_MODE = "adafruit"
    _HW = True
except Exception:
    try:
        from gpiozero import LED, Buzzer, MotionSensor
        from picamera2 import Picamera2
        GPIO_MODE = "gpiozero"
        _HW = True
    except Exception as e:
        logger.warning(f"No GPIO libs ({e}); mock mode.")
        GPIO_MODE = "mock"
        _HW = False


class security_module:
    """Motion, LED, buzzer, camera; mock-safe for PC."""

    def __init__(self, config_file="config.json"):
        self.config = load_config(config_file)
        self.image_dir = "captured_images"
        os.makedirs(self.image_dir, exist_ok=True)

        logger.info(f"Security module starting: GPIO_MODE={GPIO_MODE}, camera_enabled={self.config.get('camera_enabled', True)}")

        self._pir = self._led = self._buzzer = self._cam = None

        if GPIO_MODE == "adafruit":
            try:
                self._pir = digitalio.DigitalInOut(board.D6)
                self._pir.direction = digitalio.Direction.INPUT
                self._led = digitalio.DigitalInOut(board.D16)
                self._led.direction = digitalio.Direction.OUTPUT
                self._buzzer = digitalio.DigitalInOut(board.D26)
                self._buzzer.direction = digitalio.Direction.OUTPUT
                if self.config.get("camera_enabled", True):
                    self._cam = Picamera2(); self._cam.start()
            except Exception as e:
                logger.warning(f"Adafruit init fail: {e}")

        elif GPIO_MODE == "gpiozero":
            try:
                self._pir = MotionSensor(6)
                self._led = LED(16)
                self._buzzer = Buzzer(26)
                if self.config.get("camera_enabled", True):
                    self._cam = Picamera2(); self._cam.start()
            except Exception as e:
                logger.warning(f"gpiozero init fail: {e}")

        # Log which components were successfully initialized
        present = {
            'pir': bool(self._pir),
            'led': bool(self._led),
            'buzzer': bool(self._buzzer),
            'camera': bool(self._cam)
        }
        logger.info(f"Security hardware presence: {present}")

    def _set_led(self, on):
        if self._led is not None:
            self._led.value = bool(on) if GPIO_MODE == "adafruit" else (self._led.on() if on else self._led.off())

    def _set_buzzer(self, on):
        if self._buzzer is not None:
            self._buzzer.value = bool(on) if GPIO_MODE == "adafruit" else (self._buzzer.on() if on else self._buzzer.off())

    def capture_image(self):
        if self._cam is None:
            return None
        try:
            frame = self._cam.capture_array()
            filename = os.path.join(self.image_dir, f"motion_{datetime.now():%Y%m%d_%H%M%S}.jpg")
            import cv2
            cv2.imwrite(filename, frame)
            return filename
        except Exception as e:
            logger.warning(f"Camera error: {e}")
            return None

    def get_security_data(self):
        motion = False
        if self._pir is not None:
            try:
                motion = bool(self._pir.value) if GPIO_MODE == "adafruit" else self._pir.motion_detected
            except Exception as e:
                logger.warning(f"PIR read fail: {e}")

        led_status = buzzer_status = 0
        image_path = None

        if motion:
            logger.info("Motion detected.")
            self._set_led(True); led_status = 1
            self._set_buzzer(True); buzzer_status = 1
            time.sleep(0.7)
            self._set_buzzer(False); buzzer_status = 0
            image_path = self.capture_image()
        else:
            self._set_led(False)
            self._set_buzzer(False)

        return {
            "timestamp": datetime.now().isoformat(),
            "motion_detected": motion,
            "image_path": image_path,
            "led_status": led_status,
            "buzzer_status": buzzer_status
        }
