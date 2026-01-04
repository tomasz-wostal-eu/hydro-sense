"""
DS18B20 temperature sensor interface via 1-Wire.

Features:
- Auto-discovery of DS18B20 sensors
- Multiple sensor support (unique IDs)
- Celsius/Fahrenheit conversion
- Error handling for sensor disconnection
- Thread-safe access
"""

import os
import glob
import time
import threading
from typing import Optional, Dict, List
from dataclasses import dataclass

from app.config import TEMP_W1_BASE_DIR, TEMP_UNIT
from app.logger import logger


@dataclass
class TemperatureReading:
    """Single temperature reading from DS18B20."""
    sensor_id: str
    celsius: float
    fahrenheit: float
    timestamp: float
    valid: bool
    error: Optional[str] = None


class DS18B20Sensor:
    """Single DS18B20 sensor interface."""

    def __init__(self, sensor_id: str):
        self.sensor_id = sensor_id
        self.device_file = os.path.join(TEMP_W1_BASE_DIR, sensor_id, 'w1_slave')

    def read_raw(self) -> List[str]:
        """Read raw data from sensor file."""
        try:
            with open(self.device_file, 'r') as f:
                return f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Sensor {self.sensor_id} not found")
        except Exception as e:
            raise IOError(f"Failed to read sensor {self.sensor_id}: {e}")

    def read_temperature(self) -> TemperatureReading:
        """
        Read temperature from sensor with validation.

        Returns:
            TemperatureReading with temperature data or error
        """
        try:
            lines = self.read_raw()

            # Check CRC validation (first line ends with 'YES')
            if len(lines) < 2 or not lines[0].strip().endswith('YES'):
                return TemperatureReading(
                    sensor_id=self.sensor_id,
                    celsius=0.0,
                    fahrenheit=0.0,
                    timestamp=time.time(),
                    valid=False,
                    error="CRC validation failed"
                )

            # Parse temperature from second line (format: "t=12345")
            equals_pos = lines[1].find('t=')
            if equals_pos == -1:
                return TemperatureReading(
                    sensor_id=self.sensor_id,
                    celsius=0.0,
                    fahrenheit=0.0,
                    timestamp=time.time(),
                    valid=False,
                    error="Temperature data not found"
                )

            temp_string = lines[1][equals_pos + 2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0

            return TemperatureReading(
                sensor_id=self.sensor_id,
                celsius=temp_c,
                fahrenheit=temp_f,
                timestamp=time.time(),
                valid=True
            )

        except FileNotFoundError as e:
            return TemperatureReading(
                sensor_id=self.sensor_id,
                celsius=0.0,
                fahrenheit=0.0,
                timestamp=time.time(),
                valid=False,
                error=f"Sensor disconnected: {e}"
            )
        except Exception as e:
            return TemperatureReading(
                sensor_id=self.sensor_id,
                celsius=0.0,
                fahrenheit=0.0,
                timestamp=time.time(),
                valid=False,
                error=f"Read error: {e}"
            )


class TemperatureSensorManager:
    """
    Manages multiple DS18B20 temperature sensors.

    Supports:
    - Auto-discovery of sensors
    - Specific sensor configuration
    - Thread-safe access
    - Graceful error handling
    """

    def __init__(self, sensor_ids: Optional[List[str]] = None):
        """
        Initialize temperature sensor manager.

        Args:
            sensor_ids: List of sensor IDs (e.g., ['28-00000xxxxx']).
                       If None or empty, auto-detect all DS18B20 sensors.
        """
        self.lock = threading.Lock()
        self.sensors: Dict[str, DS18B20Sensor] = {}

        # Load kernel modules
        self._load_kernel_modules()

        # Discover or configure sensors
        if sensor_ids and len(sensor_ids) > 0:
            # Use specific sensor IDs
            for sensor_id in sensor_ids:
                self.sensors[sensor_id] = DS18B20Sensor(sensor_id)
            logger.info(f"Configured {len(self.sensors)} temperature sensors: {sensor_ids}")
        else:
            # Auto-discover all DS18B20 sensors
            self.discover_sensors()

    def _load_kernel_modules(self):
        """Load required kernel modules for 1-Wire."""
        try:
            os.system('modprobe w1-gpio')
            os.system('modprobe w1-therm')
            logger.debug("Loaded 1-Wire kernel modules")
        except Exception as e:
            logger.warning(f"Failed to load kernel modules: {e}")

    def discover_sensors(self) -> List[str]:
        """
        Auto-discover DS18B20 sensors connected to 1-Wire bus.

        Returns:
            List of discovered sensor IDs
        """
        try:
            # DS18B20 sensors start with '28-'
            device_folders = glob.glob(os.path.join(TEMP_W1_BASE_DIR, '28-*'))

            discovered_ids = []
            for folder in device_folders:
                sensor_id = os.path.basename(folder)
                discovered_ids.append(sensor_id)
                self.sensors[sensor_id] = DS18B20Sensor(sensor_id)

            if discovered_ids:
                logger.info(f"Discovered {len(discovered_ids)} DS18B20 sensors: {discovered_ids}")
            else:
                logger.warning("No DS18B20 sensors discovered. Check wiring and 1-Wire configuration.")

            return discovered_ids

        except Exception as e:
            logger.error(f"Failed to discover sensors: {e}", exc_info=True)
            return []

    def read_all(self) -> Dict[str, TemperatureReading]:
        """
        Read temperature from all configured sensors.

        Returns:
            Dictionary mapping sensor_id to TemperatureReading
        """
        with self.lock:
            readings = {}
            for sensor_id, sensor in self.sensors.items():
                reading = sensor.read_temperature()
                readings[sensor_id] = reading

                if reading.valid:
                    logger.debug(f"Sensor {sensor_id}: {reading.celsius:.2f}°C")
                else:
                    logger.warning(f"Sensor {sensor_id} read failed: {reading.error}")

            return readings

    def read_sensor(self, sensor_id: str) -> Optional[TemperatureReading]:
        """
        Read temperature from specific sensor.

        Args:
            sensor_id: Sensor ID (e.g., '28-00000xxxxx')

        Returns:
            TemperatureReading or None if sensor not found
        """
        with self.lock:
            sensor = self.sensors.get(sensor_id)
            if not sensor:
                logger.warning(f"Sensor {sensor_id} not configured")
                return None

            return sensor.read_temperature()

    def get_sensor_ids(self) -> List[str]:
        """Get list of configured sensor IDs."""
        return list(self.sensors.keys())

    def refresh_sensors(self) -> List[str]:
        """Re-discover sensors (useful for hot-plug support)."""
        with self.lock:
            self.sensors.clear()
            return self.discover_sensors()
