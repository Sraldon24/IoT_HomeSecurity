# security_module.py
import logging, os, time
from datetime import datetime
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Hardware imports with graceful fallback
try:
    import board, digitalio
    from picamera2 import Picamera2
    import cv2
    _HW = True
except Exception as e:
    logger.warning(f"Hardware libs unavailable ({e}); running in mock mode.")
    board = digitalio = Picamera2 = cv2 = None  # type: ignore
    _HW = False

class security_module:
    """PIR motion; toggles LED/buzzer; captures image; returns statuses + image_path."""

    def __init__(self, config_file='config.json'):
        self.config = load_config(config_file)

        self.image_dir = "captured_images"
        os.makedirs(self.image_dir, exist_ok=True)

        self._pir = None
        self._led = None
        self._buzzer = None
        self._cam = None

        if _HW:
            try:
                self._pir = digitalio.DigitalInOut(board.D6)
                self._pir.direction = digitalio.Direction.INPUT

                self._led = digitalio.DigitalInOut(board.D16)
                self._led.direction = digitalio.Direction.OUTPUT
                self._led.value = False

                self._buzzer = digitalio.DigitalInOut(board.D26)
                self._buzzer.direction = digitalio.Direction.OUTPUT
                self._buzzer.value = False

                if self.config.get("camera_enabled", True):
                    self._cam = Picamera2()
                    self._cam.start()
            except Exception as e:
                logger.warning(f"GPIO/Camera init failed; mock mode: {e}")
                self._pir = self._led = self._buzzer = self._cam = None

    def _set_led(self, on: bool):
        if self._led is not None:
            self._led.value = bool(on)

    def _set_buzzer(self, on: bool):
        if self._buzzer is not None:
            self._buzzer.value = bool(on)

    def capture_image(self):
        if self._cam is None:
            return None
        try:
            frame = self._cam.capture_array()
            filename = os.path.join(self.image_dir, f"motion_{datetime.now():%Y%m%d_%H%M%S}.jpg")
            import cv2  # safe (already available if _cam exists)
            cv2.imwrite(filename, frame)
            logger.info(f"Captured image: {filename}")
            return filename
        except Exception as e:
            logger.warning(f"Camera error: {e}")
            return None

    def get_security_data(self):
        """Run one poll: read PIR, actuate LED/buzzer, optionally capture image."""
        motion = False
        if self._pir is not None:
            try:
                motion = bool(self._pir.value)
            except Exception as e:
                logger.warning(f"PIR read failed: {e}")

        image_path = None
        led_status = 0
        buzzer_status = 0

        if motion:
            logger.info("Motion detected.")
            self._set_led(True);  led_status = 1
            self._set_buzzer(True); buzzer_status = 1
            time.sleep(0.7)  # short beep
            self._set_buzzer(False); buzzer_status = 0  # buzzer off after chirp

            image_path = self.capture_image()
        else:
            self._set_led(False);  led_status = 0
            self._set_buzzer(False); buzzer_status = 0

        return {
            "timestamp": datetime.now().isoformat(),
            "motion_detected": motion,
            "image_path": image_path,
            "led_status": led_status,
            "buzzer_status": buzzer_status
        }
