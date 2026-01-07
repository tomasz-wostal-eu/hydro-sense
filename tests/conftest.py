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
