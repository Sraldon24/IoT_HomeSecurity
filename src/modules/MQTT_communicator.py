import logging
import threading
import uuid
import time
from typing import Any, Optional
import paho.mqtt.client as mqtt
from modules.config_loader import load_config

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MQTT_communicator:
    """Stable Adafruit IO MQTT client (TLS enforced, port 8883)."""

    def __init__(self, config_file: str = "config.json"):
        self.config = load_config(config_file)
        self.mqtt_client: Optional[mqtt.Client] = None
        self.mqtt_connected = False
        self._connected_event = threading.Event()
        self.reconnect_attempts = 0
        self._use_tls = True  # always use TLS for Adafruit IO
        self.setup_mqtt()

    # -------------------------------------------------------------------
    def _create_client(self) -> mqtt.Client:
        """Create a new client with unique ID to avoid rc=5 session conflicts."""
        client_id = f"DomiSafe-{uuid.uuid4().hex[:6]}"
        return mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

    # -------------------------------------------------------------------
    def setup_mqtt(self):
        host = self.config.get("MQTT_BROKER", "io.adafruit.com")
        port = int(self.config.get("MQTT_PORT", 8883))  # TLS port
        keepalive = int(self.config.get("MQTT_KEEPALIVE", 60))
        user = str(self.config.get("ADAFRUIT_IO_USERNAME", "")).strip()
        key = str(self.config.get("ADAFRUIT_IO_KEY", "")).strip()

        cfg_client_id = self.config.get("MQTT_CLIENT_ID", None)
        if cfg_client_id is None:
            self.mqtt_client = self._create_client()
        elif isinstance(cfg_client_id, str) and cfg_client_id == "":
            self.mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
        else:
            self.mqtt_client = mqtt.Client(client_id=str(cfg_client_id), protocol=mqtt.MQTTv311)

        self.mqtt_client.username_pw_set(user, key)

        try:
            self.mqtt_client.enable_logger(logger)
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_disconnect = self.on_disconnect
            self.mqtt_client.on_publish = self.on_publish

            # Force TLS for Adafruit IO
            self.config["MQTT_PORT"] = 8883
            logger.info(f"🔒 Forcing TLS connection to {host}:8883")
            self.mqtt_client.tls_set()

            masked_key = f"{key[:4]}…{key[-4:]}" if len(key) >= 8 else "****"
            logger.info(f"MQTT config: user={user!r}, key_mask={masked_key}, host={host!r}, port={port}")

            # Connect securely
            self.mqtt_client.connect(host, port, keepalive)
            self.mqtt_client.loop_start()

            if self._connected_event.wait(timeout=10.0) and self.mqtt_connected:
                logger.info("✅ Connected securely to Adafruit IO MQTT (TLS 8883)")
            else:
                raise RuntimeError("MQTT connection timeout")

        except Exception as e:
            logger.error(f"❌ MQTT setup failed: {e}")
            self.mqtt_connected = False

    # -------------------------------------------------------------------
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.mqtt_connected = True
            self.reconnect_attempts = 0
            logger.info("✅ Connected to Adafruit IO MQTT broker (TLS).")
        else:
            self.mqtt_connected = False
            reasons = {
                1: "Unacceptable protocol version",
                2: "Identifier rejected",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            reason = reasons.get(rc, f"Unknown code {rc}")
            logger.error(f"❌ Connection failed (rc={rc}): {reason}")

        self._connected_event.set()

    # -------------------------------------------------------------------
    def on_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        logger.warning(f"Disconnected (rc={rc})")

        if rc != 0:
            time.sleep(2)
            logger.info("Attempting reconnection...")
            self.reconnect()

    # -------------------------------------------------------------------
    def reconnect(self):
        try:
            port = int(self.config.get("MQTT_PORT", 8883))
            host = self.config.get("MQTT_BROKER", "io.adafruit.com")
            self._connected_event.clear()
            self.mqtt_client = self._create_client()
            user = str(self.config.get("ADAFRUIT_IO_USERNAME", "")).strip()
            key = str(self.config.get("ADAFRUIT_IO_KEY", "")).strip()
            self.mqtt_client.username_pw_set(user, key)
            self.mqtt_client.enable_logger(logger)
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_disconnect = self.on_disconnect
            self.mqtt_client.on_publish = self.on_publish
            self.mqtt_client.tls_set()
            self.mqtt_client.connect(host, port, 60)
            self.mqtt_client.loop_start()
            logger.info("🔁 Reconnection attempt started.")
        except Exception as e:
            logger.error(f"❌ Reconnection failed: {e}")

    # -------------------------------------------------------------------
    def on_publish(self, client, userdata, mid):
        logger.debug(f"Message {mid} published successfully.")

    # -------------------------------------------------------------------
    def send_to_adafruit_io(self, feed_name: str, value: Any) -> bool:
        if not self.mqtt_client or not self.mqtt_connected:
            logger.warning("⚠️ MQTT not connected – skipping publish.")
            return False

        topic = f"{self.config['ADAFRUIT_IO_USERNAME']}/feeds/{feed_name}"
        payload = "null" if value is None else str(value)

        try:
            info = self.mqtt_client.publish(topic, payload)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Sent to {feed_name}: {payload}")
                return True
            else:
                logger.error(f"Publish failed (rc={info.rc}) for feed {feed_name}")
                return False
        except Exception as e:
            logger.error(f"MQTT publish exception: {e}")
            return False