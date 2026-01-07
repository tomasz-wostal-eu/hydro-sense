"""
Water level monitoring using mechanical float switches.

Features:
- GPIO input monitoring for float switches
- Active HIGH/LOW support
- Debouncing for mechanical switches
- Thread-safe state tracking
- Callback system for state changes
"""

import threading
import time
from typing import Optional, Callable
from enum import Enum
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

from app.logger import logger


class WaterLevel(str, Enum):
    """Water level state enumeration."""
    OK = "OK"  # Water level is adequate
    LOW = "LOW"  # Water level is too low


class WaterLevelSensor:
    """
    Water level sensor using mechanical float switch.

    Monitors GPIO input pin and detects water level state.
    Supports debouncing for stable readings.
    """

    def __init__(
        self,
        gpio_pin: int,
        active_high: bool = True,
        debounce_time: float = 0.5,
        on_state_change: Optional[Callable[[WaterLevel, dict], None]] = None
    ):
        """
        Initialize water level sensor.

        Args:
            gpio_pin: BCM GPIO pin number for sensor input
            active_high: True if sensor outputs HIGH when water is low
            debounce_time: Debounce time in seconds for mechanical switch
            on_state_change: Callback function called when state changes (receives WaterLevel and info dict)
        """
        self.gpio_pin = gpio_pin
        self.active_high = active_high
        self.debounce_time = debounce_time
        self.on_state_change = on_state_change

        self.current_level = WaterLevel.OK
        self.lock = threading.Lock()
        self.last_change_time = datetime.now()

        # Monitoring thread
        self.monitoring = threading.Event()
        self.monitor_thread: Optional[threading.Thread] = None

        if GPIO_AVAILABLE:
            # Setup GPIO pin as input with pull-up resistor
            # For conductive sensors: pull-up ensures disconnected = HIGH = water LOW
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Read initial state
            self._update_level()

            # Start monitoring thread
            self.monitoring.set()
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="WaterLevelMonitor",
                daemon=True
            )
            self.monitor_thread.start()

            logger.info(
                f"Water level sensor initialized on GPIO {gpio_pin} "
                f"(active_high={active_high}, debounce={debounce_time}s, "
                f"initial_level={self.current_level})"
            )
        else:
            logger.warning(
                f"Water level sensor initialized without GPIO "
                f"(GPIO library not available)"
            )

    def _read_gpio(self) -> bool:
        """Read current GPIO state."""
        if not GPIO_AVAILABLE:
            return False
        return GPIO.input(self.gpio_pin) == GPIO.HIGH

    def _update_level(self) -> Optional[WaterLevel]:
        """
        Update water level based on GPIO state.

        Returns:
            New water level if changed, None otherwise
        """
        gpio_state = self._read_gpio()

        # Determine water level based on active_high setting
        if self.active_high:
            new_level = WaterLevel.LOW if gpio_state else WaterLevel.OK
        else:
            new_level = WaterLevel.OK if gpio_state else WaterLevel.LOW

        with self.lock:
            if new_level != self.current_level:
                old_level = self.current_level
                self.current_level = new_level
                self.last_change_time = datetime.now()

                logger.info(
                    f"Water level changed: {old_level} → {new_level} "
                    f"(GPIO={gpio_state})"
                )

                # Construct info dict while we have the lock
                water_info = {
                    "gpio_pin": self.gpio_pin,
                    "active_high": self.active_high,
                    "current_level": new_level,
                    "last_change": self.last_change_time.isoformat(),
                    "gpio_state": gpio_state,
                }

                # Call callback if registered
                if self.on_state_change:
                    logger.debug(f"Calling water level callback with {new_level}")
                    try:
                        self.on_state_change(new_level, water_info)
                        logger.debug(f"Water level callback completed")
                    except Exception as e:
                        logger.error(f"Error in water level callback: {e}", exc_info=True)
                else:
                    logger.warning(f"No callback registered for water level change")

                return new_level

        return None

    def _monitor_loop(self):
        """
        Background monitoring loop.

        Continuously monitors GPIO input and updates water level state
        with debouncing.
        """
        logger.info("Water level monitoring loop started")

        stable_gpio_state = self._read_gpio()
        stable_since = time.time()

        while self.monitoring.is_set():
            try:
                current_gpio_state = self._read_gpio()

                # Check if state changed
                if current_gpio_state != stable_gpio_state:
                    # State changed, reset debounce timer
                    stable_gpio_state = current_gpio_state
                    stable_since = time.time()
                else:
                    # State stable, check if debounce time elapsed
                    if time.time() - stable_since >= self.debounce_time:
                        # State has been stable for debounce_time, update level
                        self._update_level()
                        stable_since = time.time()  # Reset timer

                # Sleep briefly to avoid busy-waiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in water level monitoring loop: {e}")
                time.sleep(1.0)

        logger.info("Water level monitoring loop stopped")

    def get_level(self) -> WaterLevel:
        """Get current water level."""
        with self.lock:
            return self.current_level

    def get_info(self) -> dict:
        """
        Get sensor information.

        Returns:
            Dictionary with sensor status
        """
        with self.lock:
            return {
                "gpio_pin": self.gpio_pin,
                "active_high": self.active_high,
                "current_level": self.current_level,
                "last_change": self.last_change_time.isoformat(),
                "gpio_state": self._read_gpio() if GPIO_AVAILABLE else None,
            }

    def cleanup(self):
        """Stop monitoring and cleanup GPIO."""
        logger.info("Cleaning up water level sensor...")

        # Stop monitoring thread
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitoring.clear()
            self.monitor_thread.join(timeout=2.0)
            if self.monitor_thread.is_alive():
                logger.warning("Water level monitoring thread did not stop gracefully")

        # Cleanup GPIO
        if GPIO_AVAILABLE:
            GPIO.cleanup(self.gpio_pin)

        logger.info("Water level sensor cleaned up")
