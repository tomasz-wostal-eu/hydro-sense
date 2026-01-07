"""Tests for DS18B20 temperature sensor interface."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from app.temperature import (
    TemperatureReading,
    DS18B20Sensor,
    TemperatureSensorManager,
)


class TestTemperatureReading:
    """Tests for TemperatureReading dataclass."""

    def test_valid_reading(self):
        """Should create valid temperature reading."""
        reading = TemperatureReading(
            sensor_id='28-test-01',
            celsius=22.5,
            fahrenheit=72.5,
            timestamp=1234567890.0,
            valid=True
        )

        assert reading.sensor_id == '28-test-01'
        assert reading.celsius == 22.5
        assert reading.fahrenheit == 72.5
        assert reading.timestamp == 1234567890.0
        assert reading.valid is True
        assert reading.error is None

    def test_invalid_reading_with_error(self):
        """Should create invalid reading with error message."""
        reading = TemperatureReading(
            sensor_id='28-test-01',
            celsius=0.0,
            fahrenheit=0.0,
            timestamp=1234567890.0,
            valid=False,
            error='Sensor disconnected'
        )

        assert reading.valid is False
        assert reading.error == 'Sensor disconnected'


class TestDS18B20Sensor:
    """Tests for DS18B20Sensor."""

    def test_initialization(self):
        """Should initialize DS18B20 sensor."""
        with patch('app.temperature.TEMP_W1_BASE_DIR', '/sys/bus/w1/devices/'):
            sensor = DS18B20Sensor('28-test-sensor-01')

            assert sensor.sensor_id == '28-test-sensor-01'
            assert sensor.device_file == '/sys/bus/w1/devices/28-test-sensor-01/w1_slave'

    def test_read_raw_success(self):
        """Should read raw data from sensor file."""
        sensor = DS18B20Sensor('28-test-01')
        mock_data = "50 01 4b 46 7f ff 0c 10 1c : crc=1c YES\n50 01 4b 46 7f ff 0c 10 1c t=21000\n"

        with patch('builtins.open', mock_open(read_data=mock_data)):
            lines = sensor.read_raw()

            assert len(lines) == 2
            assert 'YES' in lines[0]
            assert 't=' in lines[1]

    def test_read_raw_file_not_found(self):
        """Should raise FileNotFoundError when sensor not found."""
        sensor = DS18B20Sensor('28-nonexistent')

        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError, match='Sensor 28-nonexistent not found'):
                sensor.read_raw()

    def test_read_raw_io_error(self):
        """Should raise IOError on read failure."""
        sensor = DS18B20Sensor('28-test-01')

        with patch('builtins.open', side_effect=IOError('Permission denied')):
            with pytest.raises(IOError, match='Failed to read sensor'):
                sensor.read_raw()

    def test_read_temperature_success(self):
        """Should read temperature successfully."""
        sensor = DS18B20Sensor('28-test-01')
        mock_data = "50 01 4b 46 7f ff 0c 10 1c : crc=1c YES\n50 01 4b 46 7f ff 0c 10 1c t=21000\n"

        with patch('builtins.open', mock_open(read_data=mock_data)):
            reading = sensor.read_temperature()

            assert reading.sensor_id == '28-test-01'
            assert reading.valid is True
            assert reading.celsius == 21.0
            assert abs(reading.fahrenheit - 69.8) < 0.1
            assert reading.error is None

    def test_read_temperature_crc_failure(self):
        """Should handle CRC validation failure."""
        sensor = DS18B20Sensor('28-test-01')
        mock_data = "50 01 4b 46 7f ff 0c 10 1c : crc=1c NO\n50 01 4b 46 7f ff 0c 10 1c t=21000\n"

        with patch('builtins.open', mock_open(read_data=mock_data)):
            reading = sensor.read_temperature()

            assert reading.valid is False
            assert reading.error == 'CRC validation failed'

    def test_read_temperature_no_data(self):
        """Should handle missing temperature data."""
        sensor = DS18B20Sensor('28-test-01')
        mock_data = "50 01 4b 46 7f ff 0c 10 1c : crc=1c YES\nInvalid data\n"

        with patch('builtins.open', mock_open(read_data=mock_data)):
            reading = sensor.read_temperature()

            assert reading.valid is False
            assert reading.error == 'Temperature data not found'

    def test_read_temperature_sensor_disconnected(self):
        """Should handle disconnected sensor."""
        sensor = DS18B20Sensor('28-test-01')

        with patch('builtins.open', side_effect=FileNotFoundError):
            reading = sensor.read_temperature()

            assert reading.valid is False
            assert 'Sensor disconnected' in reading.error

    def test_read_temperature_generic_error(self):
        """Should handle generic read errors."""
        sensor = DS18B20Sensor('28-test-01')

        with patch('builtins.open', side_effect=Exception('Unexpected error')):
            reading = sensor.read_temperature()

            assert reading.valid is False
            assert 'Read error' in reading.error

    def test_read_temperature_single_line(self):
        """Should handle single-line response (missing second line)."""
        sensor = DS18B20Sensor('28-test-01')
        mock_data = "50 01 4b 46 7f ff 0c 10 1c : crc=1c YES\n"

        with patch('builtins.open', mock_open(read_data=mock_data)):
            reading = sensor.read_temperature()

            assert reading.valid is False
            # Single line means len(lines) < 2, which triggers CRC check first
            assert reading.error in ['CRC validation failed', 'Temperature data not found']

    def test_temperature_conversion(self):
        """Should convert temperature values correctly."""
        sensor = DS18B20Sensor('28-test-01')

        # Test 0°C
        mock_data = "... YES\n... t=0\n"
        with patch('builtins.open', mock_open(read_data=mock_data)):
            reading = sensor.read_temperature()
            assert reading.celsius == 0.0
            assert reading.fahrenheit == 32.0

        # Test negative temperature
        mock_data = "... YES\n... t=-5000\n"
        with patch('builtins.open', mock_open(read_data=mock_data)):
            reading = sensor.read_temperature()
            assert reading.celsius == -5.0
            assert abs(reading.fahrenheit - 23.0) < 0.1


class TestTemperatureSensorManager:
    """Tests for TemperatureSensorManager."""

    @patch('app.temperature.os.system')
    @patch('app.temperature.glob.glob', return_value=[])
    def test_initialization_no_sensors(self, mock_glob, mock_system):
        """Should initialize without sensors."""
        manager = TemperatureSensorManager()
        assert len(manager.sensors) == 0

    @patch('app.temperature.os.system')
    @patch('app.temperature.glob.glob', return_value=[
        '/sys/bus/w1/devices/28-sensor-01',
        '/sys/bus/w1/devices/28-sensor-02',
    ])
    def test_initialization_with_auto_discovery(self, mock_glob, mock_system):
        """Should auto-discover sensors."""
        manager = TemperatureSensorManager()

        assert len(manager.sensors) == 2
        assert '28-sensor-01' in manager.sensors
        assert '28-sensor-02' in manager.sensors

    @patch('app.temperature.os.system')
    def test_initialization_with_specific_sensors(self, mock_system):
        """Should use specific sensor IDs."""
        sensor_ids = ['28-specific-01', '28-specific-02']
        manager = TemperatureSensorManager(sensor_ids=sensor_ids)

        assert len(manager.sensors) == 2
        assert '28-specific-01' in manager.sensors
        assert '28-specific-02' in manager.sensors

    @patch('app.temperature.os.system')
    @patch('app.temperature.glob.glob', return_value=[])
    def test_load_kernel_modules_called(self, mock_glob, mock_system):
        """Should attempt to load kernel modules."""
        TemperatureSensorManager()

        # Verify modprobe was called for both modules
        assert mock_system.call_count == 2
        calls = [call[0][0] for call in mock_system.call_args_list]
        assert 'modprobe w1-gpio' in calls
        assert 'modprobe w1-therm' in calls

    @patch('app.temperature.os.system', side_effect=Exception('Module load failed'))
    @patch('app.temperature.glob.glob', return_value=[])
    def test_load_kernel_modules_failure(self, mock_glob, mock_system):
        """Should handle kernel module load failure gracefully."""
        manager = TemperatureSensorManager()  # Should not raise

        assert manager is not None
        assert len(manager.sensors) == 0

    @patch('app.temperature.os.system')
    @patch('app.temperature.glob.glob', return_value=[
        '/sys/bus/w1/devices/28-sensor-01',
        '/sys/bus/w1/devices/28-sensor-02',
        '/sys/bus/w1/devices/28-sensor-03',
    ])
    def test_discover_sensors(self, mock_glob, mock_system):
        """Should discover DS18B20 sensors."""
        manager = TemperatureSensorManager()

        assert len(manager.sensors) == 3
        assert '28-sensor-01' in manager.sensors
        assert '28-sensor-02' in manager.sensors
        assert '28-sensor-03' in manager.sensors

    @patch('app.temperature.os.system')
    @patch('app.temperature.glob.glob', return_value=[])
    def test_discover_sensors_none_found(self, mock_glob, mock_system):
        """Should handle no sensors found."""
        manager = TemperatureSensorManager()
        assert len(manager.sensors) == 0

    @patch('app.temperature.os.system')
    @patch('app.temperature.glob.glob', side_effect=Exception('Glob error'))
    def test_discover_sensors_error(self, mock_glob, mock_system):
        """Should handle discovery errors."""
        manager = TemperatureSensorManager()

        # discover_sensors is called in __init__, errors are caught
        assert len(manager.sensors) == 0

    @patch('app.temperature.os.system')
    def test_read_all(self, mock_system):
        """Should read from all sensors."""
        sensor_ids = ['28-test-01', '28-test-02']
        manager = TemperatureSensorManager(sensor_ids=sensor_ids)

        mock_data = "... YES\n... t=22500\n"
        with patch('builtins.open', mock_open(read_data=mock_data)):
            readings = manager.read_all()

            assert len(readings) == 2
            assert '28-test-01' in readings
            assert '28-test-02' in readings
            assert readings['28-test-01'].valid is True

    @patch('app.temperature.os.system')
    def test_read_all_with_errors(self, mock_system):
        """Should handle errors when reading sensors."""
        sensor_ids = ['28-test-01']
        manager = TemperatureSensorManager(sensor_ids=sensor_ids)

        with patch('builtins.open', side_effect=FileNotFoundError):
            readings = manager.read_all()

            assert len(readings) == 1
            assert readings['28-test-01'].valid is False

    @patch('app.temperature.os.system')
    def test_read_sensor(self, mock_system):
        """Should read from specific sensor."""
        sensor_ids = ['28-test-01', '28-test-02']
        manager = TemperatureSensorManager(sensor_ids=sensor_ids)

        mock_data = "... YES\n... t=23000\n"
        with patch('builtins.open', mock_open(read_data=mock_data)):
            reading = manager.read_sensor('28-test-01')

            assert reading is not None
            assert reading.sensor_id == '28-test-01'
            assert reading.celsius == 23.0

    @patch('app.temperature.os.system')
    def test_read_sensor_not_found(self, mock_system):
        """Should return None for non-existent sensor."""
        manager = TemperatureSensorManager(sensor_ids=['28-test-01'])

        reading = manager.read_sensor('28-nonexistent')

        assert reading is None

    @patch('app.temperature.os.system')
    def test_get_sensor_ids(self, mock_system):
        """Should return list of sensor IDs."""
        sensor_ids = ['28-test-01', '28-test-02', '28-test-03']
        manager = TemperatureSensorManager(sensor_ids=sensor_ids)

        ids = manager.get_sensor_ids()

        assert ids == sensor_ids

    def test_refresh_sensors(self):
        """Should refresh sensor list."""
        with patch('app.temperature.os.system'):
            with patch('app.temperature.glob.glob', return_value=[
                '/sys/bus/w1/devices/28-sensor-01',
                '/sys/bus/w1/devices/28-sensor-02',
            ]):
                manager = TemperatureSensorManager()

            # Mock additional sensors
            with patch('app.temperature.glob.glob', return_value=[
                '/sys/bus/w1/devices/28-sensor-01',
                '/sys/bus/w1/devices/28-sensor-02',
                '/sys/bus/w1/devices/28-sensor-03',
            ]):
                refreshed = manager.refresh_sensors()

                assert len(refreshed) == 3
                assert '28-sensor-03' in refreshed

    @patch('app.temperature.os.system')
    def test_thread_safety(self, mock_system):
        """Should handle concurrent access safely."""
        import threading

        sensor_ids = ['28-test-01', '28-test-02']
        manager = TemperatureSensorManager(sensor_ids=sensor_ids)
        errors = []

        mock_data = "... YES\n... t=22000\n"

        def read_repeatedly():
            try:
                with patch('builtins.open', mock_open(read_data=mock_data)):
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
