"""
Mock hardware implementations for testing without physical devices.

Enable mock mode by setting MOCK_MODE=true in .env

Features:
- Mock LED strip with visual logging
- Mock temperature sensors with realistic variations
- Compatible interface with real hardware
"""

import threading
import time
import random
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.logger import logger


class MockPixelStrip:
    """Mock implementation of rpi_ws281x.PixelStrip"""

    def __init__(self, num, pin, freq_hz, dma, invert, brightness, channel):
        self._num_pixels = num
        self._pixels = [(0, 0, 0)] * num
        self._brightness = brightness
        logger.info(f"[MOCK] Initialized LED strip: {num} pixels on pin {pin}")

    def begin(self):
        """Initialize the strip (no-op for mock)"""
        logger.debug("[MOCK] LED strip initialized")

    def numPixels(self):
        """Return number of pixels"""
        return self._num_pixels

    def setPixelColor(self, n, color):
        """Set pixel color"""
        if 0 <= n < self._num_pixels:
            # Extract RGB from 24-bit color
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            self._pixels[n] = (r, g, b)

    def show(self):
        """Update the strip (log for mock)"""
        # Sample first, middle, and last pixels for logging
        if self._num_pixels > 0:
            first = self._pixels[0]
            middle = self._pixels[self._num_pixels // 2]
            last = self._pixels[-1]

            # Only log if there's visible color (not all black)
            if any(sum(pixel) > 0 for pixel in [first, middle, last]):
                logger.debug(
                    f"[MOCK] LED update: first={first}, "
                    f"middle={middle}, last={last}"
                )


def Color(r, g, b):
    """Mock Color function (compatible with rpi_ws281x)"""
    return (r << 16) | (g << 8) | b


class MockLedStrip:
    """
    Mock LED strip implementation.

    Drop-in replacement for app.led.LedStrip when MOCK_MODE=true
    """

    def __init__(self, count: int):
        """Initialize mock LED strip"""
        logger.info(f"[MOCK] Creating LED strip with {count} LEDs")
        self.count = count
        self.brightness = 1.0
        self.gamma = self._build_gamma_table(2.2)

        # Use mock hardware
        self.strip = MockPixelStrip(
            count, 18, 800000, 10, False, 255, 0
        )
        self.strip.begin()

        # Thread safety locks (same as real implementation)
        self.lock = threading.Lock()
        self.anim_lock = threading.Lock()

        logger.info("[MOCK] LED strip ready (mock mode)")

    def _build_gamma_table(self, gamma: float):
        """Generate gamma correction lookup table"""
        return [int(pow(i / 255.0, gamma) * 255.0 + 0.5) for i in range(256)]

    def set_brightness(self, level: float):
        """Set global brightness"""
        with self.lock:
            self.brightness = max(0.0, min(1.0, level))
            logger.debug(f"[MOCK] Brightness set to {self.brightness:.2f}")

    def _apply_pipeline(self, r: int, g: int, b: int):
        """Apply brightness and gamma correction"""
        r = self.gamma[int(r * self.brightness)]
        g = self.gamma[int(g * self.brightness)]
        b = self.gamma[int(b * self.brightness)]
        return Color(r, g, b)

    def set_rgb(self, r: int, g: int, b: int):
        """Set all pixels to RGB color"""
        with self.lock:
            color = self._apply_pipeline(r, g, b)
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, color)
            self.strip.show()
            logger.info(f"[MOCK] Set RGB: ({r}, {g}, {b})")

    def set_hsv(self, h: float, s: float, v: float):
        """Set all pixels to HSV color"""
        import colorsys
        h = (h % 360) / 360.0
        s = max(0.0, min(1.0, s))
        v = max(0.0, min(1.0, v))

        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        self.set_rgb(int(r * 255), int(g * 255), int(b * 255))

    def off(self):
        """Turn off all LEDs"""
        with self.lock:
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()
            logger.info("[MOCK] LEDs turned off")

    def set_pixel_array(self, colors: list[tuple[int, int, int]]):
        """Set individual pixel colors from array"""
        with self.lock:
            for i, (r, g, b) in enumerate(colors):
                if i >= self.strip.numPixels():
                    break
                color = self._apply_pipeline(r, g, b)
                self.strip.setPixelColor(i, color)
            self.strip.show()

    def set_pixel(self, index: int, r: int, g: int, b: int):
        """Set single pixel color"""
        with self.lock:
            if 0 <= index < self.strip.numPixels():
                color = self._apply_pipeline(r, g, b)
                self.strip.setPixelColor(index, color)
                self.strip.show()


@dataclass
class MockTemperatureReading:
    """Mock temperature reading"""
    sensor_id: str
    celsius: float
    fahrenheit: float
    timestamp: float
    valid: bool
    error: Optional[str] = None


class MockDS18B20Sensor:
    """
    Mock DS18B20 temperature sensor.

    Simulates realistic temperature variations.
    """

    def __init__(self, sensor_id: str, base_temp: float = 22.0):
        """
        Initialize mock sensor.

        Args:
            sensor_id: Sensor ID (e.g., '28-mock-sensor-01')
            base_temp: Base temperature in Celsius (default: 22.0°C)
        """
        self.sensor_id = sensor_id
        self.base_temp = base_temp
        # Add small random offset per sensor for variety
        self.offset = random.uniform(-1.0, 1.0)
        logger.debug(f"[MOCK] Created temperature sensor: {sensor_id} (base: {base_temp}°C)")

    def read_temperature(self):
        """
        Read mock temperature with realistic variation.

        Simulates:
        - Small random variations (±0.5°C)
        - Slow drift over time
        """
        # Add time-based slow drift
        drift = 0.5 * (time.time() % 100) / 100.0

        # Add small random noise
        noise = random.uniform(-0.5, 0.5)

        # Calculate final temperature
        temp_c = self.base_temp + self.offset + drift + noise
        temp_f = temp_c * 9.0 / 5.0 + 32.0

        return MockTemperatureReading(
            sensor_id=self.sensor_id,
            celsius=temp_c,
            fahrenheit=temp_f,
            timestamp=time.time(),
            valid=True
        )


class MockTemperatureSensorManager:
    """
    Mock temperature sensor manager.

    Drop-in replacement for app.temperature.TemperatureSensorManager
    """

    def __init__(self, sensor_ids: Optional[List[str]] = None):
        """
        Initialize mock temperature sensor manager.

        Args:
            sensor_ids: List of sensor IDs. If None, creates default mock sensors.
        """
        self.lock = threading.Lock()
        self.sensors: Dict[str, MockDS18B20Sensor] = {}

        if sensor_ids and len(sensor_ids) > 0:
            # Use provided sensor IDs
            for i, sensor_id in enumerate(sensor_ids):
                base_temp = 20.0 + i * 2.0  # Different temps for each sensor
                self.sensors[sensor_id] = MockDS18B20Sensor(sensor_id, base_temp)
            logger.info(f"[MOCK] Configured {len(self.sensors)} mock temperature sensors: {sensor_ids}")
        else:
            # Create default mock sensors
            default_sensors = [
                ('28-mock-sensor-01', 22.0),  # Room temp
                ('28-mock-sensor-02', 25.0),  # Aquarium temp
            ]
            for sensor_id, base_temp in default_sensors:
                self.sensors[sensor_id] = MockDS18B20Sensor(sensor_id, base_temp)
            logger.info(f"[MOCK] Auto-configured {len(self.sensors)} default mock sensors")

    def discover_sensors(self) -> List[str]:
        """Return list of mock sensor IDs"""
        return list(self.sensors.keys())

    def read_all(self) -> Dict[str, MockTemperatureReading]:
        """Read temperature from all mock sensors"""
        with self.lock:
            readings = {}
            for sensor_id, sensor in self.sensors.items():
                reading = sensor.read_temperature()
                readings[sensor_id] = reading
                logger.debug(f"[MOCK] Sensor {sensor_id}: {reading.celsius:.2f}°C")
            return readings

    def read_sensor(self, sensor_id: str) -> Optional[MockTemperatureReading]:
        """Read temperature from specific mock sensor"""
        with self.lock:
            sensor = self.sensors.get(sensor_id)
            if not sensor:
                logger.warning(f"[MOCK] Sensor {sensor_id} not found")
                return None
            return sensor.read_temperature()

    def get_sensor_ids(self) -> List[str]:
        """Get list of mock sensor IDs"""
        return list(self.sensors.keys())

    def refresh_sensors(self) -> List[str]:
        """Refresh mock sensors (no-op, returns current list)"""
        return self.discover_sensors()


# ============================================================================
# Mock Relay Control
# ============================================================================


class MockRelay:
    """Mock relay for testing without GPIO hardware."""

    def __init__(self, config):
        """
        Initialize mock relay.

        Args:
            config: RelayConfig object
        """
        from app.relay import RelayState
        from datetime import datetime

        self.config = config
        self.state = config.default_state
        self.lock = threading.Lock()

        # Auto-shutoff timer (same as real relay)
        self.shutoff_timer: Optional[threading.Timer] = None
        self.shutoff_time: Optional[datetime] = None

        logger.info(
            f"[MOCK] Relay '{config.name}' initialized on GPIO {config.gpio_pin} "
            f"(active_low={config.active_low}, default={config.default_state}, "
            f"max_on_time={config.max_on_time}s)"
        )

    def _cancel_shutoff_timer(self):
        """Cancel any active auto-shutoff timer."""
        if self.shutoff_timer:
            self.shutoff_timer.cancel()
            self.shutoff_timer = None
            self.shutoff_time = None

    def _start_shutoff_timer(self):
        """Start auto-shutoff timer if max_on_time is configured."""
        from datetime import datetime, timedelta

        if self.config.max_on_time <= 0:
            return

        self._cancel_shutoff_timer()
        self.shutoff_time = datetime.now() + timedelta(seconds=self.config.max_on_time)

        warning_time = max(0, self.config.max_on_time - 5)
        if warning_time > 0:
            warning_timer = threading.Timer(
                warning_time,
                lambda: logger.warning(
                    f"[MOCK] Relay '{self.config.name}' will auto-shutoff in 5 seconds"
                )
            )
            warning_timer.daemon = True
            warning_timer.start()

        self.shutoff_timer = threading.Timer(
            self.config.max_on_time,
            self._auto_shutoff
        )
        self.shutoff_timer.daemon = True
        self.shutoff_timer.start()

        logger.info(
            f"[MOCK] Relay '{self.config.name}' auto-shutoff timer started ({self.config.max_on_time}s)"
        )

    def _auto_shutoff(self):
        """Auto-shutoff callback."""
        logger.warning(f"[MOCK] Relay '{self.config.name}' AUTO-SHUTOFF triggered")
        self.turn_off()

    def get_time_remaining(self) -> Optional[float]:
        """Get remaining time before auto-shutoff."""
        from datetime import datetime

        if not self.shutoff_time:
            return None

        remaining = (self.shutoff_time - datetime.now()).total_seconds()
        return max(0, remaining)

    def turn_on(self) -> bool:
        """Turn mock relay ON."""
        from app.relay import RelayState

        with self.lock:
            if self.state == RelayState.ON:
                return False

            self.state = RelayState.ON
            logger.info(f"[MOCK] Relay '{self.config.name}' turned ON")

            # Start auto-shutoff timer
            self._start_shutoff_timer()

            return True

    def turn_off(self) -> bool:
        """Turn mock relay OFF."""
        from app.relay import RelayState

        with self.lock:
            if self.state == RelayState.OFF:
                return False

            # Cancel timer
            self._cancel_shutoff_timer()

            self.state = RelayState.OFF
            logger.info(f"[MOCK] Relay '{self.config.name}' turned OFF")
            return True

    def set_state(self, state) -> bool:
        """Set mock relay to specific state."""
        from app.relay import RelayState

        if state == RelayState.ON:
            return self.turn_on()
        else:
            return self.turn_off()

    def toggle(self):
        """Toggle mock relay state."""
        from app.relay import RelayState

        with self.lock:
            new_state = RelayState.OFF if self.state == RelayState.ON else RelayState.ON
            self.state = new_state
            logger.info(f"[MOCK] Relay '{self.config.name}' toggled to {new_state}")
            return new_state

    def get_state(self):
        """Get current mock relay state."""
        return self.state

    def cleanup(self):
        """Cleanup mock relay and cancel timers."""
        # Cancel any active timer
        self._cancel_shutoff_timer()
        logger.info(f"[MOCK] Relay '{self.config.name}' cleaned up")


class MockRelayManager:
    """Mock relay manager for testing without GPIO hardware."""

    def __init__(self, relay_configs: List, enable_watchdog: Optional[bool] = None):
        """
        Initialize mock relay manager.

        Args:
            relay_configs: List of RelayConfig objects
            enable_watchdog: Enable watchdog (None=auto-detect pytest, False=disabled, True=enabled)
        """
        self.relays: Dict[str, MockRelay] = {}
        self.lock = threading.Lock()

        for config in relay_configs:
            self.relays[config.id] = MockRelay(config)

        logger.info(f"[MOCK] RelayManager initialized with {len(self.relays)} relays")

        # Start watchdog monitoring if enabled
        from app.config import RELAY_WATCHDOG_ENABLED, RELAY_WATCHDOG_INTERVAL
        import sys

        # Auto-detect pytest - disable watchdog in tests to prevent thread leaks
        if enable_watchdog is None:
            is_pytest = 'pytest' in sys.modules
            self.watchdog_enabled = RELAY_WATCHDOG_ENABLED and not is_pytest
        else:
            self.watchdog_enabled = enable_watchdog and RELAY_WATCHDOG_ENABLED

        self.watchdog_interval = RELAY_WATCHDOG_INTERVAL
        self.watchdog_running = threading.Event()
        self.watchdog_thread: Optional[threading.Thread] = None

        if self.watchdog_enabled and len(self.relays) > 0:
            self.watchdog_running.set()
            self.watchdog_thread = threading.Thread(
                target=self._watchdog_loop,
                name="MockRelayWatchdog",
                daemon=True
            )
            self.watchdog_thread.start()
            logger.info(
                f"[MOCK] Relay watchdog monitoring started "
                f"(interval={self.watchdog_interval}s, relays={len(self.relays)})"
            )

    def turn_on(self, relay_id: str) -> bool:
        """Turn on specific mock relay."""
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")
        return self.relays[relay_id].turn_on()

    def turn_off(self, relay_id: str) -> bool:
        """Turn off specific mock relay."""
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")
        return self.relays[relay_id].turn_off()

    def set_state(self, relay_id: str, state) -> bool:
        """Set mock relay to specific state."""
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")
        return self.relays[relay_id].set_state(state)

    def toggle(self, relay_id: str):
        """Toggle specific mock relay."""
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")
        return self.relays[relay_id].toggle()

    def get_state(self, relay_id: str):
        """Get state of specific mock relay."""
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")
        return self.relays[relay_id].get_state()

    def get_all_states(self) -> Dict:
        """Get states of all mock relays."""
        with self.lock:
            return {relay_id: relay.get_state() for relay_id, relay in self.relays.items()}

    def turn_all_on(self) -> Dict[str, bool]:
        """Turn on all mock relays."""
        results = {}
        for relay_id, relay in self.relays.items():
            results[relay_id] = relay.turn_on()
        return results

    def turn_all_off(self) -> Dict[str, bool]:
        """Turn off all mock relays."""
        results = {}
        for relay_id, relay in self.relays.items():
            results[relay_id] = relay.turn_off()
        return results

    def get_relay_ids(self) -> List[str]:
        """Get list of configured mock relay IDs."""
        return list(self.relays.keys())

    def get_relay_info(self, relay_id: str) -> Dict:
        """Get information about specific mock relay."""
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")

        relay = self.relays[relay_id]
        info = {
            "id": relay.config.id,
            "name": relay.config.name,
            "gpio_pin": relay.config.gpio_pin,
            "active_low": relay.config.active_low,
            "state": relay.get_state(),
            "default_state": relay.config.default_state,
            "max_on_time": relay.config.max_on_time,
            "auto_shutoff_enabled": relay.config.max_on_time > 0,
        }

        # Add timer info if active
        time_remaining = relay.get_time_remaining()
        if time_remaining is not None:
            info["time_remaining"] = time_remaining
            if relay.shutoff_time:
                info["will_auto_shutoff_at"] = relay.shutoff_time.isoformat()

        return info

    def get_all_info(self) -> Dict[str, Dict]:
        """Get information about all mock relays."""
        return {relay_id: self.get_relay_info(relay_id) for relay_id in self.relays.keys()}

    def _watchdog_loop(self):
        """
        Watchdog monitoring loop (mock version).

        Periodically checks relay health and max on-time.
        Runs in background thread until watchdog_running is cleared.
        """
        logger.info("[MOCK] Relay watchdog loop started")

        while self.watchdog_running.is_set():
            try:
                # Check each relay
                for relay_id, relay in self.relays.items():
                    with relay.lock:
                        # Check if relay has exceeded max on-time
                        if relay.config.max_on_time > 0 and relay.state == "ON":
                            time_remaining = relay.get_time_remaining()
                            if time_remaining is not None and time_remaining <= 0:
                                logger.warning(
                                    f"[MOCK] Watchdog: Relay '{relay.config.name}' exceeded max on-time, "
                                    f"forcing shutoff"
                                )
                                relay.turn_off()

            except Exception as e:
                logger.error(f"[MOCK] Watchdog: Error in monitoring loop: {e}")

            # Sleep for interval, but wake up if watchdog_running is cleared
            self.watchdog_running.wait(timeout=self.watchdog_interval)

        logger.info("[MOCK] Relay watchdog loop stopped")

    def cleanup(self):
        """Cleanup all mock relays."""
        logger.info("[MOCK] Cleaning up all relays...")

        # Stop watchdog thread
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            logger.info("[MOCK] Stopping relay watchdog...")
            self.watchdog_running.clear()
            self.watchdog_thread.join(timeout=2.0)
            if self.watchdog_thread.is_alive():
                logger.warning("[MOCK] Watchdog thread did not stop gracefully")
            else:
                logger.info("[MOCK] Relay watchdog stopped")

        # Cleanup all relays
        for relay in self.relays.values():
            relay.cleanup()
        logger.info("[MOCK] All relays cleaned up")


class MockWaterLevelSensor:
    """Mock water level sensor for testing without GPIO hardware."""

    def __init__(
        self,
        gpio_pin: int,
        active_high: bool = True,
        debounce_time: float = 0.5,
        on_state_change=None
    ):
        """
        Initialize mock water level sensor.

        Args:
            gpio_pin: BCM GPIO pin number (ignored in mock)
            active_high: True if sensor outputs HIGH when water is low
            debounce_time: Debounce time in seconds
            on_state_change: Callback function for state changes
        """
        from app.water_level import WaterLevel

        self.gpio_pin = gpio_pin
        self.active_high = active_high
        self.debounce_time = debounce_time
        self.on_state_change = on_state_change

        self.current_level = WaterLevel.OK  # Start with water OK
        self.lock = threading.Lock()
        self.last_change_time = datetime.now()

        # Mock monitoring thread (simplified)
        self.monitoring = threading.Event()
        self.monitor_thread: Optional[threading.Thread] = None

        logger.info(
            f"[MOCK] Water level sensor initialized on GPIO {gpio_pin} "
            f"(active_high={active_high}, initial_level={self.current_level})"
        )

    def get_level(self):
        """Get current water level."""
        from app.water_level import WaterLevel
        with self.lock:
            return self.current_level

    def set_level(self, level):
        """
        Set water level (for testing).

        Args:
            level: WaterLevel to set
        """
        from app.water_level import WaterLevel

        with self.lock:
            if level != self.current_level:
                old_level = self.current_level
                self.current_level = level
                self.last_change_time = datetime.now()

                logger.info(f"[MOCK] Water level changed: {old_level} → {level}")

                # Call callback if registered
                if self.on_state_change:
                    try:
                        water_info = {
                            "gpio_pin": self.gpio_pin,
                            "active_high": self.active_high,
                            "current_level": level,
                            "last_change": self.last_change_time.isoformat(),
                            "gpio_state": None,
                        }
                        self.on_state_change(level, water_info)
                    except Exception as e:
                        logger.error(f"[MOCK] Error in water level callback: {e}")

    def get_info(self) -> dict:
        """Get sensor information."""
        with self.lock:
            return {
                "gpio_pin": self.gpio_pin,
                "active_high": self.active_high,
                "current_level": self.current_level,
                "last_change": self.last_change_time.isoformat(),
                "gpio_state": None,  # No GPIO in mock
            }

    def cleanup(self):
        """Cleanup mock sensor."""
        logger.info(f"[MOCK] Water level sensor cleaned up")
