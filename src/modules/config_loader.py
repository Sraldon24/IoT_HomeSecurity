# modules/config_loader.py
import json
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEFAULTS: Dict[str, object] = {
    "ADAFRUIT_IO_USERNAME": "username",
    # key will be overridden by env var when present
    "ADAFRUIT_IO_KEY": "userkey",
    "MQTT_BROKER": "io.adafruit.com",
    # Default to TLS port for Adafruit IO
    "MQTT_PORT": 1883,
    "MQTT_KEEPALIVE": 60,
    # Prefer TCP, will fallback to websockets in code; allow override
    "MQTT_TRANSPORT": "tcp",

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
    loaded = False
    search_paths = []
    # 1) Provided path as-is (relative to CWD)
    search_paths.append(path)
    # 2) Project root relative to this file: ../../config.json
    try:
        module_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(module_dir, os.pardir, os.pardir))
        search_paths.append(os.path.join(project_root, os.path.basename(path)))
    except Exception:
        pass

    for candidate in search_paths:
        try:
            with open(candidate, "r") as f:
                file_cfg = json.load(f)
                file_cfg = {k.upper(): v for k, v in file_cfg.items()}
                base.update(file_cfg or {})
                logger.info(f"Loaded config from {os.path.abspath(candidate)}")
                loaded = True
                break
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.warning(f"Failed reading config {candidate}: {e}")

    if not loaded:
        logger.warning(f"Config file {path} not found; using defaults only")

    # Security: prefer environment variable
    env_key = os.getenv("ADAFRUIT_IO_KEY")
    if env_key:
        base["ADAFRUIT_IO_KEY"] = env_key
        src_key = "ENV"
    else:
        src_key = "FILE/DEFAULT"

    env_user = os.getenv("ADAFRUIT_IO_USERNAME")
    if env_user:
        base["ADAFRUIT_IO_USERNAME"] = env_user
        src_user = "ENV"
    else:
        src_user = "FILE/DEFAULT"

    # Mask secret for logs
    def _mask(s: str) -> str:
        try:
            if len(s) <= 8:
                return "****"
            return f"{s[:4]}…{s[-4:]}"
        except Exception:
            return "****"

    try:
        masked = _mask(str(base.get("ADAFRUIT_IO_KEY", "")))
        logger.info(
            f"ADAFRUIT_IO_USERNAME={base.get('ADAFRUIT_IO_USERNAME')} (source={src_user}) | "
            f"ADAFRUIT_IO_KEY={masked} (source={src_key})"
        )
    except Exception:
        pass

    # Extra diagnostics: warn if key looks like a default/placeholder or is very short
    try:
        key_val = str(base.get("ADAFRUIT_IO_KEY", ""))
        if key_val in ("userkey", "", None) or len(key_val) < 10:
            logger.warning("ADAFRUIT_IO_KEY appears to be missing or too short; verify config.json or ADAFRUIT_IO_KEY env var")
    except Exception:
        pass

    return base
