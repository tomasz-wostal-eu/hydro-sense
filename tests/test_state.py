"""Tests for LED state management."""

import pytest
import threading
import time
from datetime import datetime
from app.state import LEDState


class TestLEDState:
    """Tests for LEDState class."""

    def test_initialization(self):
        """Should initialize with default values."""
        state = LEDState()
        assert state.mode == "off"
        assert state.rgb == (0, 0, 0)
        assert state.brightness == 1.0
        assert state.gradient_config is None
        assert state.active_animation is None
        assert state.temperature_readings is None
        assert state.last_temp_update is None
        assert isinstance(state.last_updated, datetime)

    def test_update_single_field(self):
        """Should update single field."""
        state = LEDState()
        state.update(mode="rgb")
        assert state.mode == "rgb"

    def test_update_multiple_fields(self):
        """Should update multiple fields at once."""
        state = LEDState()
        state.update(mode="rgb", rgb=(255, 0, 0), brightness=0.5)
        assert state.mode == "rgb"
        assert state.rgb == (255, 0, 0)
        assert state.brightness == 0.5

    def test_update_timestamp(self):
        """Should update last_updated timestamp on update."""
        state = LEDState()
        old_timestamp = state.last_updated
        time.sleep(0.01)
        state.update(mode="rgb")
        assert state.last_updated > old_timestamp

    def test_update_ignores_private_fields(self):
        """Should not update private fields (starting with _)."""
        state = LEDState()
        state.update(_lock="invalid")
        # Should not raise error, just ignore
        assert hasattr(state, "_lock")

    def test_update_ignores_invalid_fields(self):
        """Should ignore fields that don't exist."""
        state = LEDState()
        state.update(invalid_field="value")
        # Should not raise error, just ignore
        assert not hasattr(state, "invalid_field")

    def test_thread_safe_update(self):
        """Should handle concurrent updates safely."""
        state = LEDState()
        errors = []

        def update_state(value):
            try:
                for _ in range(100):
                    state.update(brightness=value)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=update_state, args=(0.5,)),
            threading.Thread(target=update_state, args=(0.8,)),
            threading.Thread(target=update_state, args=(1.0,))
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert state.brightness in [0.5, 0.8, 1.0]

    def test_to_mqtt_payload_off(self):
        """Should convert off state to MQTT payload."""
        state = LEDState()
        state.update(mode="off")
        payload = state.to_mqtt_payload()

        assert payload == {"state": "OFF"}

    def test_to_mqtt_payload_on(self):
        """Should convert on state to MQTT payload."""
        state = LEDState()
        state.update(mode="rgb", rgb=(255, 128, 64), brightness=0.8)
        payload = state.to_mqtt_payload()

        assert payload["state"] == "ON"
        assert payload["brightness"] == int(0.8 * 255)  # 204
        assert payload["color"]["r"] == 255
        assert payload["color"]["g"] == 128
        assert payload["color"]["b"] == 64
        assert payload["color_mode"] == "rgb"
        assert payload["effect"] == "none"

    def test_to_mqtt_payload_with_animation(self):
        """Should include animation name in effect field."""
        state = LEDState()
        state.update(
            mode="sunrise",
            rgb=(255, 200, 100),
            brightness=0.6,
            active_animation="sunrise_winter"
        )
        payload = state.to_mqtt_payload()

        assert payload["state"] == "ON"
        assert payload["effect"] == "sunrise_winter"

    def test_get_snapshot(self):
        """Should return snapshot of current state."""
        state = LEDState()
        state.update(
            mode="gradient_static",
            rgb=(255, 0, 0),
            brightness=0.7,
            gradient_config={"test": "config"},
            active_animation="test_anim"
        )

        snapshot = state.get_snapshot()

        assert snapshot["mode"] == "gradient_static"
        assert snapshot["rgb"] == (255, 0, 0)
        assert snapshot["brightness"] == 0.7
        assert snapshot["gradient_config"] == {"test": "config"}
        assert snapshot["active_animation"] == "test_anim"
        assert "last_updated" in snapshot
        assert isinstance(snapshot["last_updated"], str)  # ISO format

    def test_get_snapshot_with_temperature(self):
        """Should include temperature data in snapshot if available."""
        state = LEDState()
        temp_readings = {"sensor_1": {"celsius": 22.5}}
        temp_update = datetime.now()

        state.update(
            mode="rgb",
            temperature_readings=temp_readings,
            last_temp_update=temp_update
        )

        snapshot = state.get_snapshot()

        assert snapshot["temperature_readings"] == temp_readings
        assert snapshot["last_temp_update"] == temp_update.isoformat()

    def test_get_snapshot_thread_safe(self):
        """Should provide thread-safe snapshot."""
        state = LEDState()
        errors = []

        def get_snapshots():
            try:
                for _ in range(50):
                    snapshot = state.get_snapshot()
                    assert "mode" in snapshot
            except Exception as e:
                errors.append(e)

        def update_state():
            try:
                for i in range(50):
                    state.update(brightness=i / 50.0)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=get_snapshots),
            threading.Thread(target=get_snapshots),
            threading.Thread(target=update_state)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
