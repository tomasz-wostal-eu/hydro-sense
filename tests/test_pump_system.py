"""Tests for pump automation system (relay, water level, pump automation)."""

import pytest
import time
import threading
from datetime import datetime

from app.mock_hardware import MockRelayManager, MockWaterLevelSensor
from app.relay import RelayState, RelayConfig
from app.water_level import WaterLevel
from app.pump_automation import PumpAutomation, AutomationMode


class TestMockRelayManager:
    """Tests for MockRelayManager."""

    def test_initialization(self):
        """Should initialize with relay configs."""
        configs = [
            RelayConfig(id="pump", name="Test Pump", gpio_pin=17, active_low=True, default_state=RelayState.OFF),
            RelayConfig(id="heater", name="Test Heater", gpio_pin=27, active_low=True, default_state=RelayState.OFF),
        ]
        manager = MockRelayManager(relay_configs=configs)

        assert len(manager.get_relay_ids()) == 2
        assert "pump" in manager.get_relay_ids()
        assert "heater" in manager.get_relay_ids()

    def test_turn_on(self):
        """Should turn relay ON."""
        configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        manager = MockRelayManager(relay_configs=configs)

        changed = manager.turn_on("pump")

        assert changed is True
        assert manager.get_state("pump") == RelayState.ON

    def test_turn_on_already_on(self):
        """Should return False if already ON."""
        configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        manager = MockRelayManager(relay_configs=configs)

        manager.turn_on("pump")
        changed = manager.turn_on("pump")

        assert changed is False

    def test_turn_off(self):
        """Should turn relay OFF."""
        configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        manager = MockRelayManager(relay_configs=configs)

        manager.turn_on("pump")
        changed = manager.turn_off("pump")

        assert changed is True
        assert manager.get_state("pump") == RelayState.OFF

    def test_toggle(self):
        """Should toggle relay state."""
        configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        manager = MockRelayManager(relay_configs=configs)

        assert manager.get_state("pump") == RelayState.OFF

        new_state = manager.toggle("pump")
        assert new_state == RelayState.ON

        new_state = manager.toggle("pump")
        assert new_state == RelayState.OFF

    def test_get_relay_info(self):
        """Should return relay information."""
        configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17, max_on_time=60)]
        manager = MockRelayManager(relay_configs=configs)

        info = manager.get_relay_info("pump")

        assert info["id"] == "pump"
        assert info["name"] == "Test Pump"
        assert info["gpio_pin"] == 17
        assert info["state"] == RelayState.OFF
        assert info["max_on_time"] == 60

    def test_relay_not_found(self):
        """Should raise KeyError for non-existent relay."""
        configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        manager = MockRelayManager(relay_configs=configs)

        with pytest.raises(KeyError):
            manager.turn_on("nonexistent")


class TestMockWaterLevelSensor:
    """Tests for MockWaterLevelSensor."""

    def test_initialization(self):
        """Should initialize with default OK level."""
        sensor = MockWaterLevelSensor(gpio_pin=23)

        assert sensor.gpio_pin == 23
        assert sensor.get_level() == WaterLevel.OK

    def test_set_level(self):
        """Should allow setting water level."""
        sensor = MockWaterLevelSensor(gpio_pin=23)

        sensor.set_level(WaterLevel.LOW)
        assert sensor.get_level() == WaterLevel.LOW

        sensor.set_level(WaterLevel.OK)
        assert sensor.get_level() == WaterLevel.OK

    def test_callback_on_level_change(self):
        """Should call callback when level changes."""
        callback_called = []

        def on_change(new_level, info):
            callback_called.append((new_level, info))

        sensor = MockWaterLevelSensor(gpio_pin=23, on_state_change=on_change)

        sensor.set_level(WaterLevel.LOW)

        # Callback should be called
        assert len(callback_called) == 1
        assert callback_called[0][0] == WaterLevel.LOW
        assert callback_called[0][1]["current_level"] == WaterLevel.LOW

    def test_callback_not_called_on_same_level(self):
        """Should not call callback if level doesn't change."""
        callback_called = []

        def on_change(new_level, info):
            callback_called.append(new_level)

        sensor = MockWaterLevelSensor(gpio_pin=23, on_state_change=on_change)

        sensor.set_level(WaterLevel.OK)  # Same as initial

        assert len(callback_called) == 0

    def test_get_info(self):
        """Should return sensor information."""
        sensor = MockWaterLevelSensor(gpio_pin=23, active_high=True)

        info = sensor.get_info()

        assert info["gpio_pin"] == 23
        assert info["active_high"] is True
        assert info["current_level"] == WaterLevel.OK
        assert "last_change" in info


class TestPumpAutomation:
    """Tests for PumpAutomation."""

    def test_initialization(self):
        """Should initialize pump automation."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump",
            on_interval=10,
            off_interval=10,
            max_runtime=60
        )

        assert automation.mode == AutomationMode.AUTO
        assert automation.on_interval == 10
        assert automation.off_interval == 10
        assert automation.max_runtime == 60
        assert automation.cycle_count == 0

    def test_initialization_invalid_relay(self):
        """Should raise ValueError if pump relay doesn't exist."""
        relay_configs = [RelayConfig(id="other", name="Other", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        with pytest.raises(ValueError, match="Relay 'pump' not found"):
            PumpAutomation(
                relay_manager=relay_manager,
                water_sensor=water_sensor,
                pump_relay_id="pump"
            )

    def test_set_mode(self):
        """Should change automation mode."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump"
        )

        automation.set_mode(AutomationMode.MANUAL)
        assert automation.mode == AutomationMode.MANUAL

        automation.set_mode(AutomationMode.DISABLED)
        assert automation.mode == AutomationMode.DISABLED

    def test_set_mode_turns_off_pump(self):
        """Should turn off pump when switching to MANUAL or DISABLED."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump"
        )

        # Turn pump ON
        relay_manager.turn_on("pump")
        assert relay_manager.get_state("pump") == RelayState.ON

        # Switch to MANUAL mode
        automation.set_mode(AutomationMode.MANUAL)

        # Pump should be OFF
        assert relay_manager.get_state("pump") == RelayState.OFF

    def test_get_status(self):
        """Should return automation status."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump",
            on_interval=30,
            off_interval=30,
            max_runtime=300
        )

        status = automation.get_status()

        assert status["mode"] == AutomationMode.AUTO
        assert status["water_level"] == WaterLevel.OK
        assert status["pump_state"] == RelayState.OFF
        assert status["pump_relay_id"] == "pump"
        assert status["on_interval"] == 30
        assert status["off_interval"] == 30
        assert status["max_runtime"] == 300
        assert status["cycle_count"] == 0
        assert status["total_runtime"] == 0.0

    def test_automation_starts_pump_on_low_water(self):
        """Should start pump when water level is LOW in AUTO mode."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump",
            on_interval=1,  # Short interval for testing
            off_interval=1
        )

        # Start automation
        automation.start()

        # Simulate low water
        water_sensor.set_level(WaterLevel.LOW)

        # Wait for automation to react
        time.sleep(1.5)

        # Pump should be ON
        assert relay_manager.get_state("pump") == RelayState.ON

        # Cleanup
        automation.stop()

    def test_automation_stops_pump_on_water_ok(self):
        """Should stop pump when water level returns to OK."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump",
            on_interval=1,
            off_interval=1
        )

        automation.start()

        # Simulate low water
        water_sensor.set_level(WaterLevel.LOW)
        time.sleep(1.5)

        # Pump should be running
        assert relay_manager.get_state("pump") == RelayState.ON

        # Water level OK again
        water_sensor.set_level(WaterLevel.OK)
        time.sleep(1.5)

        # Pump should be OFF
        assert relay_manager.get_state("pump") == RelayState.OFF

        automation.stop()

    def test_reset_statistics(self):
        """Should reset cycle count and runtime."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump"
        )

        # Manually set some stats
        automation.cycle_count = 10
        automation.total_runtime = 500.0

        automation.reset_statistics()

        assert automation.cycle_count == 0
        assert automation.total_runtime == 0.0

    def test_manual_mode_disables_automation(self):
        """Should not control pump when in MANUAL mode."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump",
            on_interval=1,
            off_interval=1
        )

        automation.start()
        automation.set_mode(AutomationMode.MANUAL)

        # Simulate low water
        water_sensor.set_level(WaterLevel.LOW)
        time.sleep(1.5)

        # Pump should remain OFF (automation disabled)
        assert relay_manager.get_state("pump") == RelayState.OFF

        automation.stop()


class TestIntegration:
    """Integration tests for complete pump automation system."""

    def test_full_cycle(self):
        """Should complete full automation cycle."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump",
            on_interval=2,
            off_interval=2,
            max_runtime=60
        )

        automation.start()

        # Initial state
        assert relay_manager.get_state("pump") == RelayState.OFF
        assert automation.cycle_count == 0

        # Water LOW -> pump starts
        water_sensor.set_level(WaterLevel.LOW)
        time.sleep(2.5)

        assert relay_manager.get_state("pump") == RelayState.ON
        assert automation.cycle_count >= 1

        # Wait for OFF cycle
        time.sleep(2.5)
        assert relay_manager.get_state("pump") == RelayState.OFF

        # Water OK -> pump stays off
        water_sensor.set_level(WaterLevel.OK)
        time.sleep(2.5)
        assert relay_manager.get_state("pump") == RelayState.OFF

        automation.stop()

    def test_concurrent_access(self):
        """Should handle concurrent status requests safely."""
        relay_configs = [RelayConfig(id="pump", name="Test Pump", gpio_pin=17)]
        relay_manager = MockRelayManager(relay_configs=relay_configs)
        water_sensor = MockWaterLevelSensor(gpio_pin=23)

        automation = PumpAutomation(
            relay_manager=relay_manager,
            water_sensor=water_sensor,
            pump_relay_id="pump"
        )

        errors = []

        def get_status_repeatedly():
            try:
                for _ in range(20):
                    automation.get_status()
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=get_status_repeatedly),
            threading.Thread(target=get_status_repeatedly),
            threading.Thread(target=get_status_repeatedly),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
