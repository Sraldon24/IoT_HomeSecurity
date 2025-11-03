import json, time, logging, os, sys, threading
from datetime import datetime
from modules.MQTT_communicator import MQTT_communicator
from modules.environmental_module import environmental_module
from modules.security_module import security_module
from modules.device_control_module import device_control_module
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ENV_FEEDS = {"temperature": "temperature", "humidity": "humidity", "pressure": "pressure"}
SECURITY_FEEDS = {
    "motion_detected": "motion",
    "led_status": "led_status",
    "buzzer_status": "buzzer_status",
    "image_b64": "camera_last_image",
}

class DomiSafeApp:
    def __init__(self, config_file='config.json'):
        self.config = load_config(config_file)
        self.security_check_interval = int(self.config.get("security_check_interval", 10))
        self.env_interval = int(self.config.get("env_interval", 30))
        self.last_publish_time = 0
        self.publish_cooldown = 1.5  # seconds between publishes
        self.running = True

        # Initialize modules safely
        try:
            self.mqtt_agent = MQTT_communicator(config_file)
        except Exception as e:
            logger.error(f"MQTT init failed: {e}", exc_info=True)
            self.mqtt_agent = None
        try:
            self.env_data = environmental_module(config_file)
        except Exception as e:
            logger.error(f"Env module init failed: {e}", exc_info=True)
            self.env_data = None
        try:
            self.security_data = security_module(config_file)
        except Exception as e:
            logger.error(f"Security module init failed: {e}", exc_info=True)
            self.security_data = None
        try:
            self.device_control = device_control_module(config_file)
        except Exception as e:
            logger.error(f"Device control init failed: {e}", exc_info=True)
            self.device_control = None

        os.makedirs("logs", exist_ok=True)
        time.sleep(3)

    # ---- Safe MQTT publishing ----
    def send_to_cloud(self, data, feeds):
        ok_all = True
        now = time.time()
        for field, feed in feeds.items():
            val = data.get(field)
            if val is None:
                continue
            if not self.mqtt_agent:
                ok_all = False
                continue
            # Rate limit
            if now - self.last_publish_time < self.publish_cooldown:
                time.sleep(self.publish_cooldown)
            if not self.mqtt_agent.send_to_adafruit_io(feed, val):
                ok_all = False
            self.last_publish_time = time.time()
        return ok_all

    # ---- Loop collectors ----
    def collect_environmental_data(self, now, timers):
        if self.env_data and now - timers['env_check'] >= self.env_interval:
            env = self.env_data.get_environmental_data()
            self.send_to_cloud(env, ENV_FEEDS)
            timers['env_check'] = now

    def collect_security_data(self, now, timers):
        if self.security_data and now - timers['security_check'] >= self.security_check_interval:
            sec = self.security_data.get_security_data()
            payload = {
                "motion_detected": 1 if sec.get("motion_detected") else 0,
                "led_status": sec.get("led_status"),
                "buzzer_status": sec.get("buzzer_status"),
                "image_b64": sec.get("image_b64"),
            }
            self.send_to_cloud(payload, SECURITY_FEEDS)
            timers['security_check'] = now

    # ---- Main data loop ----
    def data_collection_loop(self):
        timers = {'env_check': 0, 'security_check': 0}
        while self.running:
            now = time.time()
            self.collect_security_data(now, timers)
            self.collect_environmental_data(now, timers)
            time.sleep(1)

    def start(self):
        logger.info("Starting DomiSafe Loop")
        thread = threading.Thread(target=self.data_collection_loop, daemon=True)
        thread.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            logger.info("Stopping…")
        finally:
            thread.join()
            if self.security_data and getattr(self.security_data, "_cam", None):
                try:
                    self.security_data._cam.stop()
                except Exception:
                    pass
            logger.info("Shutdown complete")

    # ---- Hardware test mode ----
    def test_hardware(self):
        logger.info("===== HARDWARE TEST MODE =====")
        if self.security_data:
            logger.info("Checking motion sensor...")
            sec = self.security_data.get_security_data()
            logger.info(f"PIR motion detected: {sec.get('motion_detected')}")
            logger.info("Testing LED + Buzzer")
            self.security_data._set_led(True)
            self.security_data._set_buzzer(True)
            time.sleep(1)
            self.security_data._set_led(False)
            self.security_data._set_buzzer(False)
            logger.info("Testing camera...")
            img = self.security_data.capture_and_encode_image()
            if img:
                logger.info("Camera capture OK (encoded for Adafruit)")
            else:
                logger.warning("Camera test failed — no image data")
        if self.env_data:
            logger.info("Testing DHT11 sensor...")
            env = self.env_data.get_environmental_data()
            logger.info(f"Temp={env['temperature']}°C  Humidity={env['humidity']}%  Pressure={env['pressure']} hPa")
        logger.info("===== TEST COMPLETE =====")

if __name__ == "__main__":
    app = DomiSafeApp("config.json")
    # Quick hardware self-test before launching
    app.test_hardware()
    app.start()
