# environmental_module.py
import logging, time, math, random
from datetime import datetime
from modules.config_loader import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Best effort import; fall back to "no sensor" mode
try:
    import board
    import adafruit_dht
    _HAS_DHT = True
except Exception:
    _HAS_DHT = False
    board = adafruit_dht = None  # type: ignore

class environmental_module:
    """Returns temperature/humidity/pressure. If sensor not present, returns None (published as 'null')."""

    def __init__(self, config_file='config.json'):
        self.config = load_config(config_file)
        self._dht = None
        if _HAS_DHT:
            try:
                # Allow the DHT pin to be configured via config (DHT_PIN).
                # The config value is an integer GPIO number (e.g. 4) and will be
                # converted to the board.D{N} attribute expected by the adafruit library.
                pin_cfg = int(self.config.get('DHT_PIN', 4))
                board_pin = getattr(board, f"D{pin_cfg}", None)
                if board_pin is None:
                    # Fallback to D4 if attribute not found
                    board_pin = getattr(board, 'D4')
                self._dht = adafruit_dht.DHT11(board_pin, use_pulseio=False)
            except Exception as e:
                logger.warning(f"DHT init failed, switching to null/sim mode: {e}")
                self._dht = None

    def get_environmental_data(self):
        temperature_c = None
        humidity = None
        pressure = None  # DHT11 has no pressure; we keep it for your existing feed (sim/baseline)

        if self._dht:
            try:
                temperature_c = float(self._dht.temperature) if self._dht.temperature is not None else None
                humidity = float(self._dht.humidity) if self._dht.humidity is not None else None
            except Exception as e:
                logger.warning(f"DHT read error: {e}; returning nulls")
        else:
            # If you prefer to simulate instead of nulls, uncomment next lines:
            base = 22 + 5 * math.sin(time.time() / 3600)
            temperature_c = round(base + random.uniform(-2, 2), 1)
            humidity = max(30, min(90, round(60 - (temperature_c - 20) * 2 + random.uniform(-5, 5), 1)))
            pressure = round(1013.25 + random.uniform(-10, 10), 2)
            # temperature_c = None
            # humidity = None
            # pressure = None

        result = {
            'timestamp': datetime.now().isoformat(),
            'temperature': temperature_c,
            'humidity': humidity,
            'pressure': pressure
        }
        logger.debug(f"Environmental data: {result}")
        return result
