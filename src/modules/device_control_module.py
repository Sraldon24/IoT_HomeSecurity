# device_control_module.py
import json, logging
from datetime import datetime
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class device_control_module:
    def __init__(self, config_file='config.json'):
        self.config = load_config(config_file)

    def generate_device_status(self):
        devices = self.config.get('devices', ["living_room_light", "bedroom_fan"])
        now = datetime.now().isoformat()
        return [{'timestamp': now, 'device_name': d, 'status': 'off'} for d in devices]

    def get_device_status(self):
        try:
            data = self.generate_device_status()
            logger.info(f"Device status requested: {len(data)} devices")
            return data
        except Exception as e:
            logger.error(f"Error getting device status: {e}", exc_info=True)
            return []
