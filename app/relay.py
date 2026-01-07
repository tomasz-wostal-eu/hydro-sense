"""
Relay control for GPIO-based relay modules.

Features:
- Multi-channel relay support (1-8 relays)
- Thread-safe GPIO control
- Configurable active LOW/HIGH logic
- State persistence and tracking
- Safety defaults (all OFF on startup)
- Max on-time protection with auto-shutoff
- Watchdog monitoring for relay health
"""

import threading
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

from app.logger import logger


class RelayState(str, Enum):
    """Relay state enumeration."""
    ON = "ON"
    OFF = "OFF"


@dataclass
class RelayConfig:
    """Configuration for a single relay."""
    id: str  # Unique identifier (e.g., "pump", "heater")
    name: str  # Human-readable name
    gpio_pin: int  # BCM GPIO pin number
    active_low: bool = True  # True if relay activates on LOW signal
    default_state: RelayState = RelayState.OFF  # Default state on startup
    max_on_time: int = 0  # Maximum ON time in seconds (0 = unlimited)


class Relay:
    """
    Single GPIO-controlled relay.

    Supports both active-LOW and active-HIGH relay modules.
    """

    def __init__(self, config: RelayConfig):
        """
        Initialize relay.

        Args:
            config: Relay configuration
        """
        self.config = config
        self.state = RelayState.OFF
        self.lock = threading.Lock()

        # Auto-shutoff timer
        self.shutoff_timer: Optional[threading.Timer] = None
        self.shutoff_time: Optional[datetime] = None

        if GPIO_AVAILABLE:
            # Setup GPIO pin
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(config.gpio_pin, GPIO.OUT)

            # Set initial state
            self._set_gpio(config.default_state)
            self.state = config.default_state

            logger.info(
                f"Relay '{config.name}' initialized on GPIO {config.gpio_pin} "
                f"(active_low={config.active_low}, default={config.default_state}, "
                f"max_on_time={config.max_on_time}s)"
            )
        else:
            logger.warning(
                f"Relay '{config.name}' initialized without GPIO "
                f"(GPIO library not available)"
            )

    def _set_gpio(self, state: RelayState):
        """Set GPIO output based on relay state and active logic."""
        if not GPIO_AVAILABLE:
            return

        if self.config.active_low:
            # Active LOW: ON = LOW, OFF = HIGH
            gpio_value = GPIO.LOW if state == RelayState.ON else GPIO.HIGH
        else:
            # Active HIGH: ON = HIGH, OFF = LOW
            gpio_value = GPIO.HIGH if state == RelayState.ON else GPIO.LOW

        GPIO.output(self.config.gpio_pin, gpio_value)

    def _cancel_shutoff_timer(self):
        """Cancel any active auto-shutoff timer."""
        if self.shutoff_timer:
            self.shutoff_timer.cancel()
            self.shutoff_timer = None
            self.shutoff_time = None

    def _start_shutoff_timer(self):
        """Start auto-shutoff timer if max_on_time is configured."""
        if self.config.max_on_time <= 0:
            return  # No timer needed

        # Cancel any existing timer
        self._cancel_shutoff_timer()

        # Calculate shutoff time
        self.shutoff_time = datetime.now() + timedelta(seconds=self.config.max_on_time)

        # Log warning 5 seconds before shutoff
        warning_time = max(0, self.config.max_on_time - 5)
        if warning_time > 0:
            warning_timer = threading.Timer(
                warning_time,
                lambda: logger.warning(
                    f"Relay '{self.config.name}' will auto-shutoff in 5 seconds "
                    f"(max_on_time={self.config.max_on_time}s)"
                )
            )
            warning_timer.daemon = True
            warning_timer.start()

        # Create shutoff timer
        self.shutoff_timer = threading.Timer(
            self.config.max_on_time,
            self._auto_shutoff
        )
        self.shutoff_timer.daemon = True
        self.shutoff_timer.start()

        logger.info(
            f"Relay '{self.config.name}' auto-shutoff timer started "
            f"({self.config.max_on_time}s, will shutoff at {self.shutoff_time.strftime('%H:%M:%S')})"
        )

    def _auto_shutoff(self):
        """Auto-shutoff callback (called by timer)."""
        logger.warning(
            f"Relay '{self.config.name}' AUTO-SHUTOFF triggered "
            f"(max_on_time={self.config.max_on_time}s exceeded)"
        )
        self.turn_off()

    def get_time_remaining(self) -> Optional[float]:
        """
        Get remaining time before auto-shutoff.

        Returns:
            Seconds remaining, or None if timer not active
        """
        if not self.shutoff_time:
            return None

        remaining = (self.shutoff_time - datetime.now()).total_seconds()
        return max(0, remaining)

    def turn_on(self) -> bool:
        """
        Turn relay ON.

        Starts auto-shutoff timer if max_on_time is configured.

        Returns:
            True if state changed, False if already ON
        """
        with self.lock:
            if self.state == RelayState.ON:
                return False

            self._set_gpio(RelayState.ON)
            self.state = RelayState.ON
            logger.info(f"Relay '{self.config.name}' turned ON")

            # Start auto-shutoff timer
            self._start_shutoff_timer()

            return True

    def turn_off(self) -> bool:
        """
        Turn relay OFF.

        Cancels any active auto-shutoff timer.

        Returns:
            True if state changed, False if already OFF
        """
        with self.lock:
            if self.state == RelayState.OFF:
                return False

            # Cancel timer
            self._cancel_shutoff_timer()

            self._set_gpio(RelayState.OFF)
            self.state = RelayState.OFF
            logger.info(f"Relay '{self.config.name}' turned OFF")
            return True

    def set_state(self, state: RelayState) -> bool:
        """
        Set relay to specific state.

        Args:
            state: Desired relay state

        Returns:
            True if state changed
        """
        if state == RelayState.ON:
            return self.turn_on()
        else:
            return self.turn_off()

    def toggle(self) -> RelayState:
        """
        Toggle relay state.

        Returns:
            New relay state
        """
        with self.lock:
            new_state = RelayState.OFF if self.state == RelayState.ON else RelayState.ON
            self._set_gpio(new_state)
            self.state = new_state
            logger.info(f"Relay '{self.config.name}' toggled to {new_state}")
            return new_state

    def get_state(self) -> RelayState:
        """Get current relay state."""
        return self.state

    def cleanup(self):
        """Cleanup GPIO resources and cancel timers."""
        if GPIO_AVAILABLE:
            with self.lock:
                # Cancel any active timer
                self._cancel_shutoff_timer()

                self._set_gpio(RelayState.OFF)
                GPIO.cleanup(self.config.gpio_pin)
                logger.info(f"Relay '{self.config.name}' cleaned up")


class RelayManager:
    """
    Manages multiple relays.

    Features:
    - Multiple relay control
    - Thread-safe access
    - State tracking
    - Bulk operations
    - Watchdog monitoring
    """

    def __init__(self, relay_configs: List[RelayConfig]):
        """
        Initialize relay manager.

        Args:
            relay_configs: List of relay configurations
        """
        self.relays: Dict[str, Relay] = {}
        self.lock = threading.Lock()

        for config in relay_configs:
            self.relays[config.id] = Relay(config)

        logger.info(f"RelayManager initialized with {len(self.relays)} relays")

        # Start watchdog monitoring if enabled
        from app.config import RELAY_WATCHDOG_ENABLED, RELAY_WATCHDOG_INTERVAL
        self.watchdog_enabled = RELAY_WATCHDOG_ENABLED
        self.watchdog_interval = RELAY_WATCHDOG_INTERVAL
        self.watchdog_running = threading.Event()
        self.watchdog_thread: Optional[threading.Thread] = None

        if self.watchdog_enabled and len(self.relays) > 0:
            self.watchdog_running.set()
            self.watchdog_thread = threading.Thread(
                target=self._watchdog_loop,
                name="RelayWatchdog",
                daemon=True
            )
            self.watchdog_thread.start()
            logger.info(
                f"Relay watchdog monitoring started "
                f"(interval={self.watchdog_interval}s, relays={len(self.relays)})"
            )

    def turn_on(self, relay_id: str) -> bool:
        """
        Turn on specific relay.

        Args:
            relay_id: Relay identifier

        Returns:
            True if successful

        Raises:
            KeyError: If relay_id not found
        """
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")

        return self.relays[relay_id].turn_on()

    def turn_off(self, relay_id: str) -> bool:
        """
        Turn off specific relay.

        Args:
            relay_id: Relay identifier

        Returns:
            True if successful

        Raises:
            KeyError: If relay_id not found
        """
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")

        return self.relays[relay_id].turn_off()

    def set_state(self, relay_id: str, state: RelayState) -> bool:
        """
        Set relay to specific state.

        Args:
            relay_id: Relay identifier
            state: Desired state

        Returns:
            True if successful

        Raises:
            KeyError: If relay_id not found
        """
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")

        return self.relays[relay_id].set_state(state)

    def toggle(self, relay_id: str) -> RelayState:
        """
        Toggle specific relay.

        Args:
            relay_id: Relay identifier

        Returns:
            New relay state

        Raises:
            KeyError: If relay_id not found
        """
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")

        return self.relays[relay_id].toggle()

    def get_state(self, relay_id: str) -> RelayState:
        """
        Get state of specific relay.

        Args:
            relay_id: Relay identifier

        Returns:
            Current relay state

        Raises:
            KeyError: If relay_id not found
        """
        if relay_id not in self.relays:
            raise KeyError(f"Relay '{relay_id}' not found")

        return self.relays[relay_id].get_state()

    def get_all_states(self) -> Dict[str, RelayState]:
        """
        Get states of all relays.

        Returns:
            Dictionary mapping relay_id to state
        """
        with self.lock:
            return {relay_id: relay.get_state() for relay_id, relay in self.relays.items()}

    def turn_all_on(self) -> Dict[str, bool]:
        """
        Turn on all relays.

        Returns:
            Dictionary mapping relay_id to success status
        """
        results = {}
        for relay_id, relay in self.relays.items():
            results[relay_id] = relay.turn_on()
        return results

    def turn_all_off(self) -> Dict[str, bool]:
        """
        Turn off all relays.

        Returns:
            Dictionary mapping relay_id to success status
        """
        results = {}
        for relay_id, relay in self.relays.items():
            results[relay_id] = relay.turn_off()
        return results

    def get_relay_ids(self) -> List[str]:
        """Get list of configured relay IDs."""
        return list(self.relays.keys())

    def get_relay_info(self, relay_id: str) -> Dict:
        """
        Get information about specific relay.

        Args:
            relay_id: Relay identifier

        Returns:
            Dictionary with relay information

        Raises:
            KeyError: If relay_id not found
        """
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
        """
        Get information about all relays.

        Returns:
            Dictionary mapping relay_id to relay info
        """
        return {relay_id: self.get_relay_info(relay_id) for relay_id in self.relays.keys()}

    def _watchdog_loop(self):
        """
        Watchdog monitoring loop.

        Periodically checks relay health and state consistency.
        Runs in background thread until watchdog_running is cleared.
        """
        logger.info("Relay watchdog loop started")

        while self.watchdog_running.is_set():
            try:
                # Check each relay
                for relay_id, relay in self.relays.items():
                    with relay.lock:
                        # Check if relay has exceeded max on-time
                        if relay.config.max_on_time > 0 and relay.state == RelayState.ON:
                            time_remaining = relay.get_time_remaining()
                            if time_remaining is not None and time_remaining <= 0:
                                logger.warning(
                                    f"Watchdog: Relay '{relay.config.name}' exceeded max on-time, "
                                    f"forcing shutoff"
                                )
                                # We already hold the lock, so call internal methods directly
                                # instead of turn_off() which would try to acquire the lock again
                                relay._cancel_shutoff_timer()
                                relay._set_gpio(RelayState.OFF)
                                relay.state = RelayState.OFF
                                logger.info(f"Relay '{relay.config.name}' turned OFF (watchdog)")

                        # Verify GPIO state matches software state (if GPIO available)
                        if GPIO_AVAILABLE:
                            try:
                                # Read current GPIO output state
                                gpio_state = GPIO.input(relay.config.gpio_pin)

                                # Calculate expected GPIO state based on relay state and active_low
                                if relay.config.active_low:
                                    expected_gpio = GPIO.LOW if relay.state == RelayState.ON else GPIO.HIGH
                                else:
                                    expected_gpio = GPIO.HIGH if relay.state == RelayState.ON else GPIO.LOW

                                # Check for mismatch
                                if gpio_state != expected_gpio:
                                    logger.warning(
                                        f"Watchdog: GPIO state mismatch for relay '{relay.config.name}' "
                                        f"(GPIO={gpio_state}, expected={expected_gpio}, "
                                        f"software_state={relay.state}), attempting recovery"
                                    )
                                    # Attempt recovery by re-setting GPIO
                                    relay._set_gpio(relay.state)

                            except Exception as e:
                                logger.error(
                                    f"Watchdog: Error checking GPIO state for relay '{relay.config.name}': {e}"
                                )

            except Exception as e:
                logger.error(f"Watchdog: Error in monitoring loop: {e}")

            # Sleep for interval, but wake up if watchdog_running is cleared
            self.watchdog_running.wait(timeout=self.watchdog_interval)

        logger.info("Relay watchdog loop stopped")

    def cleanup(self):
        """Cleanup all relays (turn off and release GPIO)."""
        logger.info("Cleaning up all relays...")

        # Stop watchdog thread
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            logger.info("Stopping relay watchdog...")
            self.watchdog_running.clear()
            self.watchdog_thread.join(timeout=2.0)
            if self.watchdog_thread.is_alive():
                logger.warning("Watchdog thread did not stop gracefully")
            else:
                logger.info("Relay watchdog stopped")

        # Cleanup all relays
        for relay in self.relays.values():
            relay.cleanup()
        logger.info("All relays cleaned up")
