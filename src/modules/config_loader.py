# modules/config_loader.py
import json
import os
from typing import Dict, Optional

DEFAULTS: Dict[str, object] = {
    "ADAFRUIT_IO_USERNAME": "username",
    # key will be overridden by env var when present
    "ADAFRUIT_IO_KEY": "userkey",
    "MQTT_BROKER": "io.adafruit.com",
    "MQTT_PORT": 1883,
    "MQTT_KEEPALIVE": 60,

    # App timings
    "camera_enabled": True,
    "security_check_interval": 5,
    "env_interval": 30,
    "flushing_interval": 10,
    "capturing_interval": 5,
    "sync_interval": 300,
}

def load_config(path: str = "config.json", defaults: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Load JSON config and merge with defaults. Pull ADAFRUIT_IO_KEY from ENV if present."""
    base = dict(defaults or DEFAULTS)
    try:
        with open(path, "r") as f:
            file_cfg = json.load(f)
            base.update(file_cfg or {})
    except FileNotFoundError:
        # ok: stick to defaults
        pass

    # Security: prefer environment variable
    env_key = os.getenv("ADAFRUIT_IO_KEY")
    if env_key:
        base["ADAFRUIT_IO_KEY"] = env_key

    return base
