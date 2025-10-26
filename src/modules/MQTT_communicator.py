# MQTT_communicator.py
import logging
from typing import Any
import paho.mqtt.client as mqtt
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class MQTT_communicator:
    def __init__(self, config_file: str = "config.json"):
        self.config = load_config(config_file)
        self.mqtt_client: mqtt.Client | None = None
        self.mqtt_connected = False
        self.setup_mqtt()

    def setup_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(client_id="DomiSafeClient", clean_session=True)
            self.mqtt_client.username_pw_set(
                self.config["ADAFRUIT_IO_USERNAME"],
                self.config["ADAFRUIT_IO_KEY"],
            )
            self.mqtt_client.reconnect_delay_set(min_delay=1, max_delay=120)
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_disconnect = self.on_disconnect
            self.mqtt_client.on_publish = self.on_publish
            self.mqtt_client.connect(
                self.config["MQTT_BROKER"],
                int(self.config["MQTT_PORT"]),
                int(self.config["MQTT_KEEPALIVE"]),
            )
            self.mqtt_client.loop_start()
            logger.info("MQTT client initialized and loop started")
        except Exception as e:
            logger.error(f"MQTT setup failed: {e}")
            self.mqtt_connected = False

    def on_connect(self, client, userdata, flags, rc):
        self.mqtt_connected = (rc == 0)
        if self.mqtt_connected:
            logger.info("Connected to Adafruit IO MQTT broker")
        else:
            logger.error(f"MQTT connection failed, rc={rc}")

    def on_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        logger.warning("Disconnected from MQTT broker")
        try:
            client.reconnect()
            logger.info("Reconnected to broker")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")

    def on_publish(self, client, userdata, mid):
        logger.debug(f"Message {mid} published")

    def send_to_adafruit_io(self, feed_name: str, value: Any) -> bool:
        """Publish data to an Adafruit IO feed. Converts None → 'null' per requirement."""
        if not self.mqtt_client or not self.mqtt_connected:
            logger.warning("MQTT not connected – skipping publish")
            return False

        topic = f"{self.config['ADAFRUIT_IO_USERNAME']}/feeds/{feed_name}"
        payload = "null" if value is None else str(value)
        try:
            result, mid = self.mqtt_client.publish(topic, payload)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 {feed_name} ← {payload}")
                return True
            logger.error(f"Publish failed ({result}) for feed {feed_name}")
            return False
        except Exception as e:
            logger.error(f"MQTT publish exception: {e}")
            return False
