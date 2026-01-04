"""
Centralized LED state management for MQTT synchronization.

This module provides thread-safe state tracking for the LED strip,
enabling bidirectional communication between REST API, MQTT, and Home Assistant.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Any
from datetime import datetime
import threading


@dataclass
class LEDState:
    """
    Centralized LED state for MQTT publishing and synchronization.

    Thread-safe via internal lock. All updates should use the update() method.
    """

    # Current operating mode
    mode: Literal[
        "off",
        "rgb",
        "hsv",
        "gradient_static",
        "gradient_animated",
        "sunrise",
        "sunset"
    ] = "off"

    # RGB state (last known color)
    rgb: tuple[int, int, int] = (0, 0, 0)

    # Global brightness (0.0-1.0)
    brightness: float = 1.0

    # Gradient configuration (if active)
    gradient_config: Optional[dict[str, Any]] = None

    # Active animation name (if any)
    active_animation: Optional[str] = None

    # Temperature sensor data (sensor_id -> reading dict)
    temperature_readings: Optional[dict[str, Any]] = None

    # Last temperature update timestamp
    last_temp_update: Optional[datetime] = None

    # Last update timestamp
    last_updated: datetime = field(default_factory=datetime.now)

    # Thread-safe access lock
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, **kwargs) -> None:
        """
        Thread-safe state update.

        Args:
            **kwargs: State attributes to update

        Example:
            led_state.update(mode="rgb", rgb=(255, 0, 0), brightness=0.8)
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key) and not key.startswith('_'):
                    setattr(self, key, value)
            self.last_updated = datetime.now()

    def to_mqtt_payload(self) -> dict[str, Any]:
        """
        Convert state to Home Assistant-compatible MQTT JSON payload.

        Returns:
            dict: MQTT state payload for homeassistant/light/led_strip/state

        Format matches HA MQTT Light schema:
        https://www.home-assistant.io/integrations/light.mqtt/
        """
        with self._lock:
            if self.mode == "off":
                return {
                    "state": "OFF"
                }

            return {
                "state": "ON",
                "brightness": int(self.brightness * 255),  # HA expects 0-255
                "color": {
                    "r": self.rgb[0],
                    "g": self.rgb[1],
                    "b": self.rgb[2]
                },
                "color_mode": "rgb",
                "effect": self.active_animation or "none",
            }

    def get_snapshot(self) -> dict[str, Any]:
        """
        Get thread-safe snapshot of current state.

        Returns:
            dict: Current state as dictionary (for debugging/logging)
        """
        with self._lock:
            snapshot = {
                "mode": self.mode,
                "rgb": self.rgb,
                "brightness": self.brightness,
                "gradient_config": self.gradient_config,
                "active_animation": self.active_animation,
                "last_updated": self.last_updated.isoformat(),
            }

            # Add temperature data if available
            if self.temperature_readings:
                snapshot["temperature_readings"] = self.temperature_readings
                snapshot["last_temp_update"] = self.last_temp_update.isoformat() if self.last_temp_update else None

            return snapshot


# Global state instance
led_state = LEDState()
