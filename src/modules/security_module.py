import logging, os, time, threading
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
    """Motion, LED, buzzer, camera; mock-safe for PC."""

    def __init__(self, config_file="config.json"):
        self.config = load_config(config_file)
        self.image_dir = "captured_images"
        os.makedirs(self.image_dir, exist_ok=True)

        logger.info(f"Security module starting: GPIO_MODE={GPIO_MODE}, camera_enabled={self.config.get('camera_enabled', True)}")
        self._pir = self._led = self._buzzer = self._cam = None
        # motor handles: adafruit uses two digitalio pins; gpiozero uses Motor
        self._motor = None
        self._motor_pos = None
        self._motor_neg = None

        if GPIO_MODE == "adafruit":
            try:
                self._pir = digitalio.DigitalInOut(board.D6)
                self._pir.direction = digitalio.Direction.INPUT
                self._led = digitalio.DigitalInOut(board.D16)
                self._led.direction = digitalio.Direction.OUTPUT
                self._buzzer = digitalio.DigitalInOut(board.D26)
                self._buzzer.direction = digitalio.Direction.OUTPUT
                # Motor pins may be configured via config (integers referring to board.D{N}).
                mpos = self.config.get('MOTOR_POS_PIN')
                mneg = self.config.get('MOTOR_NEG_PIN')
                try:
                    if mpos is not None and mneg is not None:
                        mpos_pin = getattr(board, f"D{int(mpos)}", None)
                        mneg_pin = getattr(board, f"D{int(mneg)}", None)
                        if mpos_pin is not None and mneg_pin is not None:
                            self._motor_pos = digitalio.DigitalInOut(mpos_pin)
                            self._motor_pos.direction = digitalio.Direction.OUTPUT
                            self._motor_neg = digitalio.DigitalInOut(mneg_pin)
                            self._motor_neg.direction = digitalio.Direction.OUTPUT
                except Exception:
                    logger.warning("Motor digitalio init failed; motor disabled")
                if self.config.get("camera_enabled", True):
                    self._cam = Picamera2(); self._cam.start()
            except Exception as e:
                logger.warning(f"Adafruit init fail: {e}")

        elif GPIO_MODE == "gpiozero":
            try:
                self._pir = MotionSensor(6)
                self._led = LED(16)
                self._buzzer = Buzzer(26)
                # gpiozero Motor expects forward and backward pins
                mpos = self.config.get('MOTOR_POS_PIN')
                mneg = self.config.get('MOTOR_NEG_PIN')
                try:
                    if mpos is not None and mneg is not None:
                        self._motor = Motor(forward=int(mpos), backward=int(mneg))
                except Exception:
                    logger.warning("gpiozero Motor init failed; motor disabled")
                if self.config.get("camera_enabled", True):
                    self._cam = Picamera2(); self._cam.start()
            except Exception as e:
                logger.warning(f"gpiozero init fail: {e}")

        # Log which components were successfully initialized
        present = {
            'pir': bool(self._pir),
            'led': bool(self._led),
            'buzzer': bool(self._buzzer),
            'motor': bool(self._motor or (self._motor_pos and self._motor_neg)),
            'camera': bool(self._cam)
        }
        logger.info(f"Security hardware presence: {present}")

    def _activate_motor(self, duration: float):
        """Run motor for `duration` seconds in a background thread-safe way."""
        try:
            if GPIO_MODE == 'gpiozero' and self._motor is not None:
                try:
                    self._motor.forward()
                    time.sleep(duration)
                    self._motor.stop()
                except Exception as e:
                    logger.warning(f"gpiozero motor activation failed: {e}")
            elif GPIO_MODE == 'adafruit' and self._motor_pos is not None and self._motor_neg is not None:
                try:
                    # Apply voltage across pos (True) and neg (False)
                    self._motor_pos.value = True
                    self._motor_neg.value = False
                    time.sleep(duration)
                    self._motor_pos.value = False
                    self._motor_neg.value = False
                except Exception as e:
                    logger.warning(f"Adafruit motor activation failed: {e}")
            else:
                logger.debug("No motor configured to activate")
        except Exception:
            logger.exception("Unexpected error while running motor")

    def _run_motor_thread(self, duration: float):
        try:
            t = threading.Thread(target=self._activate_motor, args=(duration,), daemon=True)
            t.start()
        except Exception:
            logger.exception("Failed to start motor thread")

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
            # Run motor for 3 seconds on motion (non-blocking)
            try:
                self._run_motor_thread(3.0)
            except Exception:
                logger.exception("Failed to trigger motor on motion")
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
