import logging, os, time, threading, base64
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
        from gpiozero import LED, Buzzer, MotionSensor, Motor
        from picamera2 import Picamera2
        GPIO_MODE = "gpiozero"
        _HW = True
    except Exception as e:
        logger.warning(f"No GPIO libs ({e}); mock mode.")
        GPIO_MODE = "mock"
        _HW = False


class security_module:
    """Motion, LED, buzzer, motor, camera — safe for both Pi and mock."""

    def __init__(self, config_file="config.json"):
        self.config = load_config(config_file)
        self.image_dir = "captured_images"
        os.makedirs(self.image_dir, exist_ok=True)

        logger.info(f"Security module starting: GPIO_MODE={GPIO_MODE}, camera_enabled={self.config.get('camera_enabled', True)}")

        self._pir = self._led = self._buzzer = self._cam = None
        self._motor = None
        self._motor_pos = self._motor_neg = None

        if GPIO_MODE == "adafruit":
            try:
                self._pir = digitalio.DigitalInOut(board.D6)
                self._pir.direction = digitalio.Direction.INPUT
                self._led = digitalio.DigitalInOut(board.D16)
                self._led.direction = digitalio.Direction.OUTPUT
                self._buzzer = digitalio.DigitalInOut(board.D26)
                self._buzzer.direction = digitalio.Direction.OUTPUT

                # Motor setup
                mpos = self.config.get("MOTOR_POS_PIN")
                mneg = self.config.get("MOTOR_NEG_PIN")
                if mpos is not None and mneg is not None:
                    mpos_pin = getattr(board, f"D{int(mpos)}", None)
                    mneg_pin = getattr(board, f"D{int(mneg)}", None)
                    if mpos_pin and mneg_pin:
                        self._motor_pos = digitalio.DigitalInOut(mpos_pin)
                        self._motor_pos.direction = digitalio.Direction.OUTPUT
                        self._motor_neg = digitalio.DigitalInOut(mneg_pin)
                        self._motor_neg.direction = digitalio.Direction.OUTPUT

                if self.config.get("camera_enabled", True):
                    self._cam = Picamera2()
                    self._cam.start()
            except Exception as e:
                logger.warning(f"Adafruit init failed: {e}")

        elif GPIO_MODE == "gpiozero":
            try:
                self._pir = MotionSensor(6)
                self._led = LED(16)
                self._buzzer = Buzzer(26)

                mpos = self.config.get("MOTOR_POS_PIN")
                mneg = self.config.get("MOTOR_NEG_PIN")
                if mpos is not None and mneg is not None:
                    self._motor = Motor(forward=int(mpos), backward=int(mneg))

                if self.config.get("camera_enabled", True):
                    self._cam = Picamera2()
                    self._cam.start()
            except Exception as e:
                logger.warning(f"gpiozero init failed: {e}")

        present = {
            "pir": bool(self._pir),
            "led": bool(self._led),
            "buzzer": bool(self._buzzer),
            "motor": bool(self._motor or (self._motor_pos and self._motor_neg)),
            "camera": bool(self._cam),
        }
        logger.info(f"Security hardware presence: {present}")

    # ----------------------------------------------------------------------

    def _activate_motor(self, duration: float):
        """Run motor for duration seconds."""
        try:
            if GPIO_MODE == "gpiozero" and self._motor:
                self._motor.forward()
                time.sleep(duration)
                self._motor.stop()

            elif GPIO_MODE == "adafruit" and self._motor_pos and self._motor_neg:
                self._motor_pos.value = True
                self._motor_neg.value = False
                time.sleep(duration)
                self._motor_pos.value = False
                self._motor_neg.value = False
            else:
                logger.debug("No motor configured.")
        except Exception as e:
            logger.warning(f"Motor activation failed: {e}")

    def _run_motor_thread(self, duration: float):
        try:
            t = threading.Thread(target=self._activate_motor, args=(duration,), daemon=True)
            t.start()
        except Exception:
            logger.exception("Failed to start motor thread")

    def _set_led(self, on: bool):
        try:
            if self._led is None:
                return
            if GPIO_MODE == "adafruit":
                self._led.value = bool(on)
            else:
                self._led.on() if on else self._led.off()
        except Exception as e:
            logger.warning(f"LED set failed: {e}")

    def _set_buzzer(self, on: bool):
        try:
            if self._buzzer is None:
                return
            if GPIO_MODE == "adafruit":
                self._buzzer.value = bool(on)
            else:
                self._buzzer.on() if on else self._buzzer.off()
        except Exception as e:
            logger.warning(f"Buzzer set failed: {e}")

    # ----------------------------------------------------------------------

    def capture_and_encode_image(self):
        """Capture an image and return base64-encoded JPEG for Adafruit IO."""
        if self._cam is None:
            logger.warning("Camera not initialized.")
            return None

        try:
            frame = self._cam.capture_array()
            filename = os.path.join(self.image_dir, f"motion_{datetime.now():%Y%m%d_%H%M%S}.jpg")
            import cv2

            cv2.imwrite(filename, frame)
            logger.info(f"Captured image saved: {filename}")

            with open(filename, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")

            return encoded
        except Exception as e:
            logger.warning(f"Camera capture/encode failed: {e}")
            return None

    # ----------------------------------------------------------------------

    def get_security_data(self):
        """Return motion, LED/buzzer status, and encoded image."""
        motion = False
        if self._pir is not None:
            try:
                motion = bool(self._pir.value) if GPIO_MODE == "adafruit" else self._pir.motion_detected
            except Exception as e:
                logger.warning(f"PIR read failed: {e}")

        led_status = buzzer_status = 0
        image_b64 = None

        if motion:
            logger.info("Motion detected.")
            self._set_led(True)
            led_status = 1
            self._set_buzzer(True)
            buzzer_status = 1
            time.sleep(0.7)
            self._set_buzzer(False)
            buzzer_status = 0

            image_b64 = self.capture_and_encode_image()

            try:
                self._run_motor_thread(3.0)
            except Exception:
                logger.exception("Motor trigger failed.")
        else:
            self._set_led(False)
            self._set_buzzer(False)

        return {
            "timestamp": datetime.now().isoformat(),
            "motion_detected": motion,
            "image_b64": image_b64,
            "led_status": led_status,
            "buzzer_status": buzzer_status,
        }
