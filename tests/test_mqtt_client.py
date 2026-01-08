import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from app.mqtt_client import (
    get_ha_discovery_config,
    get_temp_sensor_discovery_config,
    get_relay_discovery_config,
    get_water_level_discovery_config,
    get_pump_mode_sensor_discovery_config,
    get_pump_runtime_sensor_discovery_config,
    get_pump_mode_button_discovery_config,
    MQTTService,
    MQTT_CLIENT_ID
)
from app.state import LEDState
from app.config import TEMP_UNIT
from app.relay import RelayState
from app.pump_automation import AutomationMode
from app.water_level import WaterLevel
import sys


# Mock MQTT_CLIENT_ID for consistent testing
@pytest.fixture(autouse=True)
def mock_mqtt_constants():
    with patch('app.mqtt_client.MQTT_CLIENT_ID', 'test-client-id'), \
         patch('app.mqtt_client.TOPIC_HA_CONFIG', 'homeassistant/light/test-client-id/config'), \
         patch('app.mqtt_client.TOPIC_HA_STATE', 'homeassistant/light/test-client-id/state'), \
         patch('app.mqtt_client.TOPIC_HA_COMMAND', 'homeassistant/light/test-client-id/command'), \
         patch('app.mqtt_client.TOPIC_GRADIENT_CONFIG', 'hydrosense/test-client-id/gradient/config'), \
         patch('app.mqtt_client.TOPIC_GRADIENT_COMMAND', 'hydrosense/test-client-id/gradient/command'), \
         patch('app.mqtt_client.TOPIC_GRADIENT_STATE', 'hydrosense/test-client-id/gradient/state'), \
         patch('app.mqtt_client.TOPIC_AVAILABILITY', 'hydrosense/test-client-id/availability'):
        yield

# --- Test Discovery Config Functions ---

def test_get_ha_discovery_config():
    config = get_ha_discovery_config()
    assert isinstance(config, dict)
    assert config["name"] == "LED Strip (Test Client Id)"
    assert config["unique_id"] == "led_strip_test-client-id"
    assert config["state_topic"] == "homeassistant/light/test-client-id/state"
    assert config["command_topic"] == "homeassistant/light/test-client-id/command"
    assert "device" in config
    assert config["device"]["identifiers"] == ["hydrosense_test-client-id"]

def test_get_temp_sensor_discovery_config():
    sensor_id = "28-00000abcde"
    with patch('app.mqtt_client.TEMP_UNIT', 'celsius'):
        config = get_temp_sensor_discovery_config(sensor_id)
        assert isinstance(config, dict)
        assert config["name"] == f"Temperature {sensor_id.replace('-', ' ').title()}"
        assert config["unique_id"] == f"temp_test-client-id_{sensor_id}"
        assert config["unit_of_measurement"] == "°C"
        assert config["value_template"] == "{{ value_json.temperature }}"

def test_get_relay_discovery_config():
    relay_id = "pump"
    relay_name = "Aquarium Pump"
    config = get_relay_discovery_config(relay_id, relay_name)
    assert isinstance(config, dict)
    assert config["name"] == relay_name
    assert config["unique_id"] == f"relay_test-client-id_{relay_id}"
    assert config["state_topic"] == f"homeassistant/switch/{relay_id}/state"
    assert config["command_topic"] == f"homeassistant/switch/{relay_id}/set"

def test_get_water_level_discovery_config():
    config = get_water_level_discovery_config()
    assert isinstance(config, dict)
    assert config["name"] == "Water Level"
    assert config["unique_id"] == "water_level_test-client-id"
    assert config["state_topic"] == f"hydrosense/test-client-id/water_level/state"
    assert config["payload_on"] == "OK"
    assert config["payload_off"] == "LOW"

def test_get_pump_mode_sensor_discovery_config():
    config = get_pump_mode_sensor_discovery_config()
    assert isinstance(config, dict)
    assert config["name"] == "Pump Mode"
    assert config["unique_id"] == "pump_mode_test-client-id"
    assert config["state_topic"] == f"hydrosense/test-client-id/pump_automation/state"
    assert config["value_template"] == "{{ value_json.mode }}"

def test_get_pump_runtime_sensor_discovery_config():
    config = get_pump_runtime_sensor_discovery_config()
    assert isinstance(config, dict)
    assert config["name"] == "Pump Runtime"
    assert config["unique_id"] == "pump_runtime_test-client-id"
    assert config["state_topic"] == f"hydrosense/test-client-id/pump_automation/state"
    assert config["value_template"] == "{{ value_json.total_runtime | round(1) }}"
    assert config["unit_of_measurement"] == "s"

def test_get_pump_mode_button_discovery_config():
    mode = "AUTO"
    config = get_pump_mode_button_discovery_config(mode)
    assert isinstance(config, dict)
    assert config["name"] == f"Pump Mode {mode.title()}"
    assert config["unique_id"] == f"pump_mode_auto_test-client-id"
    assert config["command_topic"] == f"hydrosense/test-client-id/pump_automation/mode/set"
    assert config["payload_press"] == mode
    assert "icon" in config


# --- Test MQTTService Methods ---

@pytest.fixture
def mock_mqtt_client_instance():
    """Mock aiomqtt.Client instance."""
    mock_client = AsyncMock()
    return mock_client

@pytest.fixture
def mock_execute_command():
    """Mock execute_command_callback."""
    return AsyncMock()

@pytest.fixture
def mqtt_service(mock_execute_command):
    """MQTTService instance with mocked dependencies."""
    service = MQTTService(mock_execute_command)
    service.client = MagicMock() # Will be replaced by AsyncMock in tests that connect
    return service

@pytest.mark.asyncio
async def test_publish_ha_discovery_all_enabled(
    mqtt_service,
    mock_mqtt_client_instance,
    mock_execute_command,
    monkeypatch
):
    """Test publishing all HA discovery configs when all features are enabled."""
    mqtt_service.client = mock_mqtt_client_instance # Assign the AsyncMock
    mqtt_service.client.publish = AsyncMock()

    # Mock app.main and its managers globally for this test
    mock_app_main = MagicMock()
    monkeypatch.setitem(sys.modules, 'app.main', mock_app_main)

    with patch('app.config.TEMP_ENABLED', True), \
         patch('app.config.RELAY_ENABLED', True), \
         patch('app.config.WATER_LEVEL_ENABLED', True), \
         patch('app.config.PUMP_AUTOMATION_ENABLED', True), \
         patch.object(mqtt_service, 'publish_water_level_state', new_callable=AsyncMock) as mock_publish_water_level_state, \
         patch.object(mqtt_service, 'publish_pump_automation_state', new_callable=AsyncMock) as mock_publish_pump_automation_state:

            # Configure mocks for app.main attributes
            mock_app_main.temp_manager = MagicMock()
            mock_app_main.temp_manager.get_sensor_ids.return_value = ["28-temp-sensor"]

            mock_app_main.relay_manager = MagicMock()
            mock_app_main.relay_manager.get_relay_ids.return_value = ["pump"]
            mock_app_main.relay_manager.get_relay_info.return_value = {"id": "pump", "name": "Test Pump", "state": RelayState.OFF}

            mock_app_main.water_sensor = MagicMock()
            mock_app_main.water_sensor.get_info.return_value = {"current_level": WaterLevel.OK, "gpio_pin": 1, "gpio_state": True, "last_change": "now", "active_high": True}

            mock_app_main.pump_automation = MagicMock()
            mock_app_main.pump_automation.get_status.return_value = {"mode": AutomationMode.AUTO}


            # Run the method under test
            await mqtt_service._publish_ha_discovery()

            # Assertions for client.publish calls
            # LED Light
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/light/test-client-id/config',
                payload=json.dumps(get_ha_discovery_config()),
                qos=1,
                retain=True,
            )

            # Temp Sensor
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/sensor/test-client-id_28-temp-sensor/config',
                payload=json.dumps(get_temp_sensor_discovery_config("28-temp-sensor")),
                qos=1,
                retain=True,
            )

            # Relay Switch
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/switch/pump/config',
                payload=json.dumps(get_relay_discovery_config("pump", "Test Pump")),
                qos=1,
                retain=True,
            )
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/switch/pump/state',
                payload="OFF", # Initial state
                qos=1,
                retain=True,
            )

            # Water Level Sensor
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/binary_sensor/water_level_test-client-id/config',
                payload=json.dumps(get_water_level_discovery_config()),
                qos=1,
                retain=True,
            )
            mock_publish_water_level_state.assert_called_once_with(
                {"current_level": WaterLevel.OK, "gpio_pin": 1, "gpio_state": True, "last_change": "now", "active_high": True}
            )

            # Pump Mode Sensor
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/sensor/pump_mode_test-client-id/config',
                payload=json.dumps(get_pump_mode_sensor_discovery_config()),
                qos=1,
                retain=True,
            )
            # Pump Runtime Sensor
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/sensor/pump_runtime_test-client-id/config',
                payload=json.dumps(get_pump_runtime_sensor_discovery_config()),
                qos=1,
                retain=True,
            )
            # Pump Mode Buttons
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/button/pump_mode_auto_test-client-id/config',
                payload=json.dumps(get_pump_mode_button_discovery_config("AUTO")),
                qos=1,
                retain=True,
            )
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/button/pump_mode_manual_test-client-id/config',
                payload=json.dumps(get_pump_mode_button_discovery_config("MANUAL")),
                qos=1,
                retain=True,
            )
            mock_mqtt_client_instance.publish.assert_any_call(
                'homeassistant/button/pump_mode_disabled_test-client-id/config',
                payload=json.dumps(get_pump_mode_button_discovery_config("DISABLED")),
                qos=1,
                retain=True,
            )
            # Pump initial state
            mock_publish_pump_automation_state.assert_called_once_with(
                {"mode": AutomationMode.AUTO}
            )
