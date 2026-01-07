"""
Configuration management with environment variable support.

All settings can be overridden via environment variables.
Automatically loads .env file if present.
"""

import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# Load .env file from project root (one level up from app/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Logging configuration
LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = os.getenv("LOG_LEVEL", "INFO")

# Mock hardware mode (for testing without physical devices)
MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").lower() == "true"

# LED hardware configuration
LED_COUNT: int = int(os.getenv("LED_COUNT", "30"))
LED_PIN: int = int(os.getenv("LED_PIN", "18"))
LED_FREQ_HZ: int = 800000
LED_DMA: int = 10
LED_CHANNEL: int = 0
LED_GAMMA: float = 2.2

# Animation configuration
ANIMATION_FPS: int = 25

# MQTT configuration
MQTT_ENABLED: bool = os.getenv("MQTT_ENABLED", "false").lower() == "true"
MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME: str | None = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD: str | None = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "led_strip")

# Gradient configuration
GRADIENT_PRESETS_FILE: str = os.getenv(
    "GRADIENT_PRESETS_FILE",
    "/home/deploy/hydrosense/data/gradient_presets.json"  # Updated for user's home
)

# Temperature sensor configuration (DS18B20)
TEMP_ENABLED: bool = os.getenv("TEMP_ENABLED", "true").lower() == "true"
TEMP_SENSOR_IDS: str = os.getenv("TEMP_SENSOR_IDS", "")  # Comma-separated list, empty = auto-detect
TEMP_UPDATE_INTERVAL: int = int(os.getenv("TEMP_UPDATE_INTERVAL", "60"))  # seconds
TEMP_UNIT: Literal["celsius", "fahrenheit"] = os.getenv("TEMP_UNIT", "celsius")
TEMP_W1_BASE_DIR: str = os.getenv("TEMP_W1_BASE_DIR", "/sys/bus/w1/devices/")

# Relay configuration
RELAY_ENABLED: bool = os.getenv("RELAY_ENABLED", "false").lower() == "true"
# Relay configuration format: "id:name:pin:active_low:default_state:max_on_time,..."
# Example: "pump:Aquarium Pump:17:true:OFF:60,heater:Heater:27:true:OFF:0"
RELAY_CONFIG: str = os.getenv("RELAY_CONFIG", "")
RELAY_PUBLISH_STATE: bool = os.getenv("RELAY_PUBLISH_STATE", "true").lower() == "true"
RELAY_WATCHDOG_ENABLED: bool = os.getenv("RELAY_WATCHDOG_ENABLED", "true").lower() == "true"
RELAY_WATCHDOG_INTERVAL: int = int(os.getenv("RELAY_WATCHDOG_INTERVAL", "30"))

# Water level sensor configuration
WATER_LEVEL_ENABLED: bool = os.getenv("WATER_LEVEL_ENABLED", "false").lower() == "true"
WATER_LEVEL_PIN: int = int(os.getenv("WATER_LEVEL_PIN", "23"))  # GPIO 23 for float switch
WATER_LEVEL_ACTIVE_HIGH: bool = os.getenv("WATER_LEVEL_ACTIVE_HIGH", "true").lower() == "true"
WATER_LEVEL_DEBOUNCE_TIME: float = float(os.getenv("WATER_LEVEL_DEBOUNCE_TIME", "0.5"))  # 500ms debounce

# Pump automation configuration
PUMP_AUTOMATION_ENABLED: bool = os.getenv("PUMP_AUTOMATION_ENABLED", "false").lower() == "true"
PUMP_RELAY_ID: str = os.getenv("PUMP_RELAY_ID", "pump")  # Which relay controls the pump
PUMP_ON_INTERVAL: int = int(os.getenv("PUMP_ON_INTERVAL", "30"))  # Pump ON time in seconds
PUMP_OFF_INTERVAL: int = int(os.getenv("PUMP_OFF_INTERVAL", "30"))  # Pump OFF time in seconds
PUMP_MAX_RUNTIME: int = int(os.getenv("PUMP_MAX_RUNTIME", "300"))  # Max continuous runtime (5 min)


def parse_relay_config():
    """
    Parse RELAY_CONFIG environment variable into list of RelayConfig objects.

    Format: "id:name:pin:active_low:default_state:max_on_time,..."

    Returns:
        List of RelayConfig objects
    """
    from app.relay import RelayConfig, RelayState

    if not RELAY_CONFIG:
        return []

    configs = []
    for relay_str in RELAY_CONFIG.split(","):
        parts = relay_str.strip().split(":")
        if len(parts) not in [5, 6]:  # Support both old (5) and new (6) formats
            continue

        relay_id, name, pin_str, active_low_str, default_state_str = parts[:5]
        max_on_time_str = parts[5] if len(parts) == 6 else "0"

        try:
            config = RelayConfig(
                id=relay_id.strip(),
                name=name.strip(),
                gpio_pin=int(pin_str.strip()),
                active_low=active_low_str.strip().lower() == "true",
                default_state=RelayState.ON if default_state_str.strip().upper() == "ON" else RelayState.OFF,
                max_on_time=int(max_on_time_str.strip())
            )
            configs.append(config)
        except ValueError as e:
            print(f"Warning: Invalid relay config '{relay_str}': {e}")
            continue

    return configs
