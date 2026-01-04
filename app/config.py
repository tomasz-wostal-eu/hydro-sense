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
