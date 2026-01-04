"""Tests for configuration management."""

import pytest
import os
from unittest.mock import patch


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_log_level(self):
        """Should default to INFO log level."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.LOG_LEVEL == "INFO"

    def test_default_led_count(self):
        """Should default to 30 LEDs."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.LED_COUNT == 30

    def test_default_led_pin(self):
        """Should default to GPIO pin 18."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.LED_PIN == 18

    def test_default_mqtt_disabled(self):
        """Should default to MQTT disabled."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.MQTT_ENABLED is False

    def test_default_temp_enabled(self):
        """Should default to temperature sensor enabled."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.TEMP_ENABLED is True


class TestConfigEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_override_log_level(self):
        """Should override LOG_LEVEL from environment."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.LOG_LEVEL == "DEBUG"

    def test_override_led_count(self):
        """Should override LED_COUNT from environment."""
        with patch.dict(os.environ, {"LED_COUNT": "60"}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.LED_COUNT == 60

    def test_override_led_pin(self):
        """Should override LED_PIN from environment."""
        with patch.dict(os.environ, {"LED_PIN": "12"}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.LED_PIN == 12

    def test_override_mqtt_enabled(self):
        """Should enable MQTT from environment."""
        with patch.dict(os.environ, {"MQTT_ENABLED": "true"}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.MQTT_ENABLED is True

    def test_mqtt_enabled_case_insensitive(self):
        """Should handle case-insensitive MQTT_ENABLED."""
        for value in ["True", "TRUE", "true"]:
            with patch.dict(os.environ, {"MQTT_ENABLED": value}, clear=True):
                from importlib import reload
                import app.config as config
                reload(config)
                assert config.MQTT_ENABLED is True

    def test_override_mqtt_broker(self):
        """Should override MQTT_BROKER from environment."""
        with patch.dict(os.environ, {"MQTT_BROKER": "192.168.1.100"}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.MQTT_BROKER == "192.168.1.100"

    def test_override_mqtt_port(self):
        """Should override MQTT_PORT from environment."""
        with patch.dict(os.environ, {"MQTT_PORT": "8883"}, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.MQTT_PORT == 8883

    def test_override_mqtt_credentials(self):
        """Should override MQTT credentials from environment."""
        env = {
            "MQTT_USERNAME": "test_user",
            "MQTT_PASSWORD": "test_pass"
        }
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.MQTT_USERNAME == "test_user"
            assert config.MQTT_PASSWORD == "test_pass"

    def test_override_temp_settings(self):
        """Should override temperature sensor settings."""
        env = {
            "TEMP_ENABLED": "false",
            "TEMP_SENSOR_IDS": "28-0123456789ab,28-0123456789cd",
            "TEMP_UPDATE_INTERVAL": "30",
            "TEMP_UNIT": "fahrenheit"
        }
        with patch.dict(os.environ, env, clear=True):
            from importlib import reload
            import app.config as config
            reload(config)
            assert config.TEMP_ENABLED is False
            assert config.TEMP_SENSOR_IDS == "28-0123456789ab,28-0123456789cd"
            assert config.TEMP_UPDATE_INTERVAL == 30
            assert config.TEMP_UNIT == "fahrenheit"


class TestConfigConstants:
    """Tests for hardcoded configuration constants."""

    def test_led_hardware_constants(self):
        """Should have correct LED hardware constants."""
        from app.config import LED_FREQ_HZ, LED_DMA, LED_CHANNEL, LED_GAMMA
        assert LED_FREQ_HZ == 800000
        assert LED_DMA == 10
        assert LED_CHANNEL == 0
        assert LED_GAMMA == 2.2

    def test_animation_fps(self):
        """Should have correct animation FPS."""
        from app.config import ANIMATION_FPS
        assert ANIMATION_FPS == 25
