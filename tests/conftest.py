"""Shared pytest fixtures for all tests."""

import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock hardware libraries BEFORE any app imports
# This must happen at module level, before pytest collects tests

# Mock rpi_ws281x
mock_ws281x = MagicMock()
mock_ws281x.PixelStrip = MagicMock
mock_ws281x.Color = MagicMock(side_effect=lambda r, g, b: (r, g, b))
sys.modules['rpi_ws281x'] = mock_ws281x

# Mock astral (solar calculations)
from datetime import datetime, timezone

mock_astral = MagicMock()
mock_location_info = MagicMock()
mock_astral.LocationInfo = mock_location_info

# Create a mock sun function that returns realistic datetime objects
def mock_sun_func(observer, date=None, tzinfo=None):
    # Return mock sunrise/sunset times with proper timezone info
    tz = timezone.utc if tzinfo is None else tzinfo
    now = datetime.now(tz)
    return {
        'sunrise': now.replace(hour=6, minute=0),
        'sunset': now.replace(hour=18, minute=0)
    }

mock_astral.sun.sun = mock_sun_func
sys.modules['astral'] = mock_astral
sys.modules['astral.sun'] = mock_astral.sun

# Mock GPIO-related modules
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()

# Now we can import app modules safely

# Now we can import app modules safely


@pytest.fixture
def mock_mqtt():
    """Mock MQTT client for testing."""
    with patch('app.mqtt_client.aiomqtt.Client') as mock:
        yield mock


@pytest.fixture
def disable_mqtt():
    """Disable MQTT for tests that don't need it."""
    with patch('app.config.MQTT_ENABLED', False):
        yield


@pytest.fixture
def disable_temperature():
    """Disable temperature sensors for tests that don't need them."""
    with patch('app.config.TEMP_ENABLED', False):
        yield


@pytest.fixture
def disable_relay():
    """Disable relay control for tests that don't need it."""
    with patch('app.config.RELAY_ENABLED', False):
        yield


@pytest.fixture
def disable_water_level():
    """Disable water level sensor for tests that don't need it."""
    with patch('app.config.WATER_LEVEL_ENABLED', False):
        yield


@pytest.fixture
def disable_pump_automation():
    """Disable pump automation for tests that don't need it."""
    with patch('app.config.PUMP_AUTOMATION_ENABLED', False):
        yield


@pytest.fixture(autouse=True)
def cleanup_pump_automations():
    """
    Auto-cleanup fixture for PumpAutomation instances.

    Ensures all PumpAutomation threads are stopped after each test,
    even if the test fails before calling stop().
    """
    # Track all PumpAutomation instances created during test
    _created_automations = []
    original_init = None

    try:
        from app.pump_automation import PumpAutomation
        original_init = PumpAutomation.__init__

        def tracked_init(self, *args, **kwargs):
            """Wrapper that tracks PumpAutomation instances."""
            original_init(self, *args, **kwargs)
            _created_automations.append(self)

        PumpAutomation.__init__ = tracked_init
    except ImportError:
        pass  # pump_automation not available in this test

    yield

    # Cleanup all tracked automations
    for automation in _created_automations:
        try:
            if hasattr(automation, 'automation_running') and automation.automation_running.is_set():
                automation.stop()
        except Exception:
            pass  # Ignore cleanup errors

    # Restore original __init__
    if original_init:
        try:
            from app.pump_automation import PumpAutomation
            PumpAutomation.__init__ = original_init
        except ImportError:
            pass
