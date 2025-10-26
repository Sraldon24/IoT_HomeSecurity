# domisafe_app.py
import json, time, logging, os,sys, threading
from datetime import datetime
# make sure modules folder is importable
sys.path.append(os.path.join(os.path.dirname(__file__), "modules"))
from MQTT_communicator import MQTT_communicator
from environmental_module import environmental_module
from security_module import security_module
from device_control_module import device_control_module
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adafruit feeds (matching your screenshot)
ENV_FEEDS = {
    "temperature": "temperature",
    "humidity": "humidity",
    "pressure": "pressure"
}
SECURITY_FEEDS = {
    "motion_detected": "motion",
    "led_status": "led_status",
    "buzzer_status": "buzzer_status",
    "camera_last_image": "camera_last_image",
}

class DomiSafeApp:
    def __init__(self, config_file='config.json'):
        self.config = load_config(config_file)

        self.security_check_interval = int(self.config.get("security_check_interval", 5))
        self.env_interval            = int(self.config.get("env_interval", 30))

        self.running = True
        self.mqtt_agent     = MQTT_communicator(config_file)
        self.env_data       = environmental_module(config_file)
        self.security_data  = security_module(config_file)
        self.device_control = device_control_module(config_file)

        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def send_to_cloud(self, data: dict, feeds: dict[str, str]):
        ok_all = True
        for field, feed in feeds.items():
            if field not in data:
                continue
            if not self.mqtt_agent.send_to_adafruit_io(feed, data[field]):
                ok_all = False
            time.sleep(0.2)
        return ok_all

    def collect_environmental_data(self, now, timers, fileh):
        if now - timers['env_check'] >= self.env_interval:
            env = self.env_data.get_environmental_data()
            fileh.write(json.dumps(env) + "\n")
            self.send_to_cloud(env, ENV_FEEDS)
            timers['env_check'] = now

    def collect_security_data(self, now, timers, fileh):
        if now - timers['security_check'] >= self.security_check_interval:
            sec = self.security_data.get_security_data()

            # persist JSONL
            today_file = os.path.join(self.log_dir, f"{datetime.now():%Y-%m-%d}_motion_events.jsonl")
            with open(today_file, "a") as f:
                json.dump(sec, f); f.write("\n")

            # cloud: push motion + statuses + last image path
            payload = {
                "motion_detected": 1 if sec["motion_detected"] else 0,
                "led_status": sec.get("led_status"),
                "buzzer_status": sec.get("buzzer_status"),
                "camera_last_image": sec.get("image_path")
            }
            self.send_to_cloud(payload, SECURITY_FEEDS)

            fileh.write(json.dumps(sec) + "\n")
            timers['security_check'] = now

    def data_collection_loop(self):
        date = datetime.now().strftime("%Y%m%d")
        env_f = f"{date}_environmental_data.txt"
        sec_f = f"{date}_security_data.txt"
        dev_f = f"{date}_device_status.txt"

        timers = {'env_check': 0, 'security_check': 0}
        last_sync = time.time()

        with open(env_f, "a", buffering=1) as ef, \
             open(sec_f, "a", buffering=1) as sf, \
             open(dev_f, "a", buffering=1) as df:

            while self.running:
                now = time.time()
                self.collect_security_data(now, timers, sf)
                self.collect_environmental_data(now, timers, ef)

                if now - last_sync > int(self.config.get("flushing_interval", 10)):
                    for fh in (ef, sf, df):
                        fh.flush(); os.fsync(fh.fileno())
                    last_sync = now

                time.sleep(self.security_check_interval)

    def start(self):
        logger.info("Starting DomiSafe Loop")
        thread = threading.Thread(target=self.data_collection_loop, daemon=True)
        thread.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping…")
        finally:
            self.running = False
            thread.join(timeout=10)
            if hasattr(self.security_data, "_cam") and self.security_data._cam:
                try:
                    self.security_data._cam.stop()
                except Exception:
                    pass
            logger.info("Shutdown complete")

if __name__ == "__main__":
    DomiSafeApp("config.json").start()
