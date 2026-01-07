"""
Pump automation based on water level sensor.

Features:
- Automatic pump control based on water level
- Interval-based operation (ON/OFF cycles)
- Safety limits (max runtime)
- Manual override capability
- Thread-safe operation
"""

import threading
import time
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum

from app.logger import logger
from app.water_level import WaterLevel, WaterLevelSensor
from app.relay import RelayManager, RelayState


class AutomationMode(str, Enum):
    """Automation mode enumeration."""
    AUTO = "AUTO"  # Automatic control based on water level
    MANUAL = "MANUAL"  # Manual control only
    DISABLED = "DISABLED"  # Automation disabled


class PumpAutomation:
    """
    Automatic pump control based on water level sensor.

    Implements interval-based operation when water level is low.
    """

    def __init__(
        self,
        relay_manager: RelayManager,
        water_sensor: WaterLevelSensor,
        pump_relay_id: str,
        on_interval: int = 30,  # seconds
        off_interval: int = 30,  # seconds
        max_runtime: int = 300,  # seconds (5 minutes default)
    ):
        """
        Initialize pump automation.

        Args:
            relay_manager: RelayManager instance
            water_sensor: WaterLevelSensor instance
            pump_relay_id: Relay ID for the pump
            on_interval: Time pump runs when water is low (seconds)
            off_interval: Time pump waits between cycles (seconds)
            max_runtime: Maximum continuous runtime before forcing stop (seconds)
        """
        self.relay_manager = relay_manager
        self.water_sensor = water_sensor
        self.pump_relay_id = pump_relay_id
        self.on_interval = on_interval
        self.off_interval = off_interval
        self.max_runtime = max_runtime

        self.mode = AutomationMode.AUTO
        self.lock = threading.Lock()

        # State tracking
        self.running_since: Optional[datetime] = None
        self.total_runtime: float = 0.0
        self.cycle_count: int = 0
        self.last_action_time = datetime.now()

        # Automation thread
        self.automation_running = threading.Event()
        self.automation_thread: Optional[threading.Thread] = None

        # Verify relay exists
        if pump_relay_id not in relay_manager.get_relay_ids():
            raise ValueError(f"Relay '{pump_relay_id}' not found in relay manager")

        logger.info(
            f"Pump automation initialized (relay={pump_relay_id}, "
            f"on={on_interval}s, off={off_interval}s, max_runtime={max_runtime}s)"
        )

    def start(self):
        """Start automation thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            logger.warning("Pump automation already running")
            return

        self.automation_running.set()
        self.automation_thread = threading.Thread(
            target=self._automation_loop,
            name="PumpAutomation",
            daemon=True
        )
        self.automation_thread.start()
        logger.info("Pump automation started")

    def stop(self):
        """Stop automation thread and turn off pump."""
        logger.info("Stopping pump automation...")

        if self.automation_thread and self.automation_thread.is_alive():
            self.automation_running.clear()
            self.automation_thread.join(timeout=2.0)
            if self.automation_thread.is_alive():
                logger.warning("Pump automation thread did not stop gracefully")

        # Ensure pump is off
        try:
            self.relay_manager.turn_off(self.pump_relay_id)
        except Exception as e:
            logger.error(f"Error turning off pump during automation stop: {e}")

        logger.info("Pump automation stopped")

    def set_mode(self, mode: AutomationMode):
        """
        Set automation mode.

        Args:
            mode: Desired automation mode
        """
        with self.lock:
            old_mode = self.mode
            self.mode = mode
            logger.info(f"Automation mode changed: {old_mode} → {mode}")

            # If switching to DISABLED, stop pump
            # MANUAL mode: don't touch the pump, let user control it
            if mode == AutomationMode.DISABLED:
                try:
                    self.relay_manager.turn_off(self.pump_relay_id)
                    self.running_since = None
                except Exception as e:
                    logger.error(f"Error turning off pump during mode change: {e}")

    def _automation_loop(self):
        """
        Main automation loop.

        Monitors water level and controls pump with interval-based operation.
        """
        logger.info("Pump automation loop started")

        while self.automation_running.is_set():
            try:
                with self.lock:
                    # Check if automation is enabled
                    if self.mode == AutomationMode.DISABLED:
                        # Disabled mode: ensure pump is off
                        if self.relay_manager.get_state(self.pump_relay_id) == RelayState.ON:
                            self.relay_manager.turn_off(self.pump_relay_id)
                            self.running_since = None
                        time.sleep(1.0)
                        continue
                    elif self.mode == AutomationMode.MANUAL:
                        # Manual mode: don't touch the pump, user controls it
                        # Just monitor, don't control
                        time.sleep(1.0)
                        continue

                    # Get current water level
                    water_level = self.water_sensor.get_level()

                    if water_level == WaterLevel.LOW:
                        # Water is low, run pump in intervals
                        self._handle_low_water()
                    else:
                        # Water is OK, ensure pump is off
                        if self.relay_manager.get_state(self.pump_relay_id) == RelayState.ON:
                            logger.info("Water level OK, turning pump OFF")
                            self.relay_manager.turn_off(self.pump_relay_id)
                            self.running_since = None

                # Sleep briefly
                time.sleep(1.0)

            except Exception as e:
                logger.error(f"Error in pump automation loop: {e}")
                time.sleep(5.0)

        logger.info("Pump automation loop stopped")

    def _handle_low_water(self):
        """
        Handle low water condition with interval-based pump operation.

        Runs pump for on_interval seconds, then waits off_interval seconds,
        and repeats. Enforces max_runtime safety limit.
        """
        current_time = time.time()
        pump_state = self.relay_manager.get_state(self.pump_relay_id)

        # Check if we've exceeded max runtime
        if self.running_since:
            elapsed = (datetime.now() - self.running_since).total_seconds()
            if elapsed >= self.max_runtime:
                logger.error(
                    f"SAFETY: Pump exceeded max runtime ({self.max_runtime}s), "
                    f"forcing OFF and disabling automation"
                )
                self.relay_manager.turn_off(self.pump_relay_id)
                self.mode = AutomationMode.DISABLED
                self.running_since = None
                return

        # Calculate time since last action
        time_since_action = (datetime.now() - self.last_action_time).total_seconds()

        if pump_state == RelayState.OFF:
            # Pump is off, check if it's time to turn it on
            if time_since_action >= self.off_interval:
                logger.info(
                    f"Water level LOW, turning pump ON for {self.on_interval}s "
                    f"(cycle #{self.cycle_count + 1})"
                )
                self.relay_manager.turn_on(self.pump_relay_id)
                self.last_action_time = datetime.now()
                self.cycle_count += 1

                # Track when continuous operation started
                if not self.running_since:
                    self.running_since = datetime.now()

        elif pump_state == RelayState.ON:
            # Pump is on, check if it's time to turn it off
            if time_since_action >= self.on_interval:
                logger.info(f"Pump ON interval complete, turning OFF for {self.off_interval}s")
                self.relay_manager.turn_off(self.pump_relay_id)
                self.last_action_time = datetime.now()

                # Update total runtime
                if self.running_since:
                    self.total_runtime += time_since_action

    def get_status(self) -> dict:
        """
        Get automation status.

        Returns:
            Dictionary with current status
        """
        with self.lock:
            pump_state = self.relay_manager.get_state(self.pump_relay_id)
            water_level = self.water_sensor.get_level()

            status = {
                "mode": self.mode,
                "water_level": water_level,
                "pump_state": pump_state,
                "pump_relay_id": self.pump_relay_id,
                "on_interval": self.on_interval,
                "off_interval": self.off_interval,
                "max_runtime": self.max_runtime,
                "cycle_count": self.cycle_count,
                "total_runtime": self.total_runtime,
                "automation_active": self.automation_running.is_set(),
            }

            # Add runtime info if pump is running
            if self.running_since:
                elapsed = (datetime.now() - self.running_since).total_seconds()
                status["running_since"] = self.running_since.isoformat()
                status["current_runtime"] = elapsed
                status["runtime_remaining"] = max(0, self.max_runtime - elapsed)

            # Add time to next action
            time_since_action = (datetime.now() - self.last_action_time).total_seconds()
            if pump_state == RelayState.ON:
                status["next_action"] = "turn_off"
                status["next_action_in"] = max(0, self.on_interval - time_since_action)
            else:
                status["next_action"] = "turn_on"
                status["next_action_in"] = max(0, self.off_interval - time_since_action)

            return status

    def reset_statistics(self):
        """Reset runtime statistics."""
        with self.lock:
            self.total_runtime = 0.0
            self.cycle_count = 0
            logger.info("Pump automation statistics reset")
