"""Tests for mock hardware implementations."""

import pytest
import time
from app.mock_hardware import (
    MockLedStrip,
    MockTemperatureSensorManager,
    MockDS18B20Sensor,
    MockPixelStrip,
    Color,
)


class TestMockPixelStrip:
    """Tests for MockPixelStrip."""

    def test_initialization(self):
        """Should initialize mock pixel strip."""
        strip = MockPixelStrip(30, 18, 800000, 10, False, 255, 0)

        assert strip._num_pixels == 30
        assert len(strip._pixels) == 30
        assert all(pixel == (0, 0, 0) for pixel in strip._pixels)

    def test_begin(self):
        """Should initialize the strip (no-op for mock)."""
        strip = MockPixelStrip(30, 18, 800000, 10, False, 255, 0)
        strip.begin()  # Should not raise

    def test_num_pixels(self):
        """Should return number of pixels."""
        strip = MockPixelStrip(30, 18, 800000, 10, False, 255, 0)
        assert strip.numPixels() == 30

    def test_set_pixel_color(self):
        """Should set pixel color."""
        strip = MockPixelStrip(30, 18, 800000, 10, False, 255, 0)
        color = Color(255, 128, 64)

        strip.setPixelColor(0, color)

        assert strip._pixels[0] == (255, 128, 64)

    def test_set_pixel_color_out_of_bounds(self):
        """Should ignore out of bounds indices."""
        strip = MockPixelStrip(30, 18, 800000, 10, False, 255, 0)
        color = Color(255, 0, 0)

        strip.setPixelColor(100, color)  # Should not raise
        strip.setPixelColor(-1, color)   # Should not raise

    def test_show(self):
        """Should trigger display update (logs for mock)."""
        strip = MockPixelStrip(30, 18, 800000, 10, False, 255, 0)
        strip.setPixelColor(0, Color(255, 0, 0))
        strip.show()  # Should not raise


class TestColorFunction:
    """Tests for Color helper function."""

    def test_color_encoding(self):
        """Should encode RGB to 24-bit color."""
        color = Color(255, 128, 64)

        # Extract components
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF

        assert r == 255
        assert g == 128
        assert b == 64

    def test_color_black(self):
        """Should encode black correctly."""
        color = Color(0, 0, 0)
        assert color == 0

    def test_color_white(self):
        """Should encode white correctly."""
        color = Color(255, 255, 255)
        assert color == (255 << 16) | (255 << 8) | 255


class TestMockLedStrip:
    """Tests for MockLedStrip."""

    def test_initialization(self):
        """Should initialize mock LED strip."""
        strip = MockLedStrip(count=30)

        assert strip.count == 30
        assert strip.brightness == 1.0
        assert len(strip.gamma) == 256
        assert strip.lock is not None
        assert strip.anim_lock is not None

    def test_set_brightness(self):
        """Should set brightness."""
        strip = MockLedStrip(count=30)

        strip.set_brightness(0.5)
        assert strip.brightness == 0.5

    def test_set_brightness_clamping(self):
        """Should clamp brightness to [0.0, 1.0]."""
        strip = MockLedStrip(count=30)

        strip.set_brightness(1.5)
        assert strip.brightness == 1.0

        strip.set_brightness(-0.5)
        assert strip.brightness == 0.0

    def test_set_rgb(self):
        """Should set all pixels to RGB color."""
        strip = MockLedStrip(count=30)
        strip.set_rgb(255, 128, 64)
        # Should not raise

    def test_set_hsv(self):
        """Should set all pixels to HSV color."""
        strip = MockLedStrip(count=30)
        strip.set_hsv(180, 1.0, 1.0)
        # Should not raise

    def test_set_hsv_hue_wrapping(self):
        """Should wrap hue values."""
        strip = MockLedStrip(count=30)
        strip.set_hsv(370, 1.0, 1.0)
        # Should not raise

    def test_off(self):
        """Should turn off all LEDs."""
        strip = MockLedStrip(count=30)
        strip.off()
        # Should not raise

    def test_set_pixel_array(self):
        """Should set individual pixel colors."""
        strip = MockLedStrip(count=30)
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
        ]
        strip.set_pixel_array(colors)
        # Should not raise

    def test_set_pixel_array_empty(self):
        """Should handle empty array."""
        strip = MockLedStrip(count=30)
        strip.set_pixel_array([])
        # Should not raise

    def test_set_pixel(self):
        """Should set single pixel color."""
        strip = MockLedStrip(count=30)
        strip.set_pixel(0, 255, 0, 0)
        # Should not raise

    def test_set_pixel_out_of_bounds(self):
        """Should ignore out of bounds indices."""
        strip = MockLedStrip(count=30)
        strip.set_pixel(100, 255, 0, 0)
        # Should not raise

    def test_gamma_table(self):
        """Should have gamma correction table."""
        strip = MockLedStrip(count=30)

        assert len(strip.gamma) == 256
        assert strip.gamma[0] == 0
        assert strip.gamma[255] == 255
        # Gamma should be non-linear
        assert strip.gamma[128] < 128


class TestMockDS18B20Sensor:
    """Tests for MockDS18B20Sensor."""

    def test_initialization(self):
        """Should initialize mock sensor."""
        sensor = MockDS18B20Sensor('28-mock-01', base_temp=22.0)

        assert sensor.sensor_id == '28-mock-01'
        assert sensor.base_temp == 22.0
        assert sensor.offset is not None

    def test_read_temperature(self):
        """Should read temperature with variations."""
        sensor = MockDS18B20Sensor('28-mock-01', base_temp=22.0)

        reading = sensor.read_temperature()

        assert reading.sensor_id == '28-mock-01'
        assert reading.valid is True
        assert reading.error is None
        assert 20.0 < reading.celsius < 25.0  # Base 22 ± variations
        assert 68.0 < reading.fahrenheit < 77.0
        assert reading.timestamp > 0

    def test_read_temperature_variations(self):
        """Should produce different readings over time."""
        sensor = MockDS18B20Sensor('28-mock-01', base_temp=22.0)

        reading1 = sensor.read_temperature()
        time.sleep(0.01)  # Small delay
        reading2 = sensor.read_temperature()

        # Readings should be slightly different due to noise
        assert reading1.celsius != reading2.celsius

    def test_celsius_to_fahrenheit_conversion(self):
        """Should convert Celsius to Fahrenheit correctly."""
        sensor = MockDS18B20Sensor('28-mock-01', base_temp=0.0)

        reading = sensor.read_temperature()

        # Verify conversion formula: F = C * 9/5 + 32
        expected_f = reading.celsius * 9.0 / 5.0 + 32.0
        assert abs(reading.fahrenheit - expected_f) < 0.01


class TestMockTemperatureSensorManager:
    """Tests for MockTemperatureSensorManager."""

    def test_initialization_no_sensors(self):
        """Should create default mock sensors when none provided."""
        manager = MockTemperatureSensorManager()

        sensor_ids = manager.get_sensor_ids()
        assert len(sensor_ids) == 2
        assert '28-mock-sensor-01' in sensor_ids
        assert '28-mock-sensor-02' in sensor_ids

    def test_initialization_with_sensor_ids(self):
        """Should use provided sensor IDs."""
        sensor_ids = ['28-test-01', '28-test-02', '28-test-03']
        manager = MockTemperatureSensorManager(sensor_ids=sensor_ids)

        assert manager.get_sensor_ids() == sensor_ids

    def test_discover_sensors(self):
        """Should return list of configured sensors."""
        manager = MockTemperatureSensorManager()

        discovered = manager.discover_sensors()
        assert len(discovered) == 2

    def test_read_all(self):
        """Should read from all sensors."""
        manager = MockTemperatureSensorManager()

        readings = manager.read_all()

        assert len(readings) == 2
        assert '28-mock-sensor-01' in readings
        assert '28-mock-sensor-02' in readings

        for reading in readings.values():
            assert reading.valid is True
            assert reading.celsius > 0

    def test_read_sensor(self):
        """Should read from specific sensor."""
        manager = MockTemperatureSensorManager()

        reading = manager.read_sensor('28-mock-sensor-01')

        assert reading is not None
        assert reading.sensor_id == '28-mock-sensor-01'
        assert reading.valid is True

    def test_read_sensor_not_found(self):
        """Should return None for non-existent sensor."""
        manager = MockTemperatureSensorManager()

        reading = manager.read_sensor('28-nonexistent')

        assert reading is None

    def test_get_sensor_ids(self):
        """Should return list of sensor IDs."""
        manager = MockTemperatureSensorManager()

        sensor_ids = manager.get_sensor_ids()

        assert isinstance(sensor_ids, list)
        assert len(sensor_ids) > 0

    def test_refresh_sensors(self):
        """Should return current sensor list."""
        manager = MockTemperatureSensorManager()

        initial_ids = manager.get_sensor_ids()
        refreshed_ids = manager.refresh_sensors()

        assert initial_ids == refreshed_ids

    def test_different_sensor_temperatures(self):
        """Should generate different base temperatures for different sensors."""
        sensor_ids = ['28-test-01', '28-test-02', '28-test-03']
        manager = MockTemperatureSensorManager(sensor_ids=sensor_ids)

        readings = manager.read_all()

        # Sensors should have different base temperatures (20, 22, 24)
        temps = [readings[sid].celsius for sid in sensor_ids]

        # Check that sensors have noticeably different temperatures
        # With base temps of 20, 22, 24, the minimum difference should be ~2 degrees
        # even with random variations
        assert max(temps) - min(temps) > 1.0

    def test_thread_safety(self):
        """Should handle concurrent access safely."""
        import threading

        manager = MockTemperatureSensorManager()
        errors = []

        def read_repeatedly():
            try:
                for _ in range(10):
                    manager.read_all()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=read_repeatedly),
            threading.Thread(target=read_repeatedly),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
