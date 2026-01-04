# HydroSense

FastAPI-based human-centric lighting control for Raspberry Pi Zero W with WS2813 LED strips.

**NEW:** Full Home Assistant integration via MQTT with bidirectional sync!
**NEW:** Aquarium biotope presets (Amazonian, Asian River, African Lake, Reef)
**NEW:** Ansible automation for easy setup and deployment
**NEW:** DS18B20 temperature sensor support

## Features

### Core Features
- **RGB and HSV color control** - Direct color setting with brightness adjustment
- **Multi-color gradients** - Static and animated gradients with 2+ color stops
- **Gradient animations** - Shift, pulse, and rainbow effects
- **Gradient presets** - Built-in presets including 4 aquarium biotope presets (amazonian, asian_river, african_lake, reef) + general presets (sunset, ocean, rainbow, fire, forest, aurora)
- **MQTT gradient control** - Create, apply, and save custom gradients via MQTT (no REST API needed)
- **Automated sunrise/sunset animations** - Realistic light transitions based on GPS coordinates
- **Season-aware color profiles** - Different color temperatures for winter, spring, summer, autumn
- **Cloud simulation** - Subtle brightness variations for natural appearance
- **Temperature Sensing** - Support for DS18B20 temperature sensors.

### Home Assistant Integration
- **MQTT bidirectional sync** - Control LEDs from HA, see state updates in real-time
- **Auto-discovery** - Automatically appears as `light.led_strip` and `sensor.temperature_*` in Home Assistant
- **Full feature support** - RGB colors, brightness, effects (rainbow, gradient shift/pulse)
- **State retention** - HA remembers LED state across restarts (MQTT retained messages)
- **Availability tracking** - Shows online/offline status in HA

### Infrastructure
- **Ansible automation** - Automated setup and deployment for multiple Raspberry Pi devices
- **Systemd service** - Auto-start on boot, auto-restart on failure
- **Graceful shutdown** - Proper cleanup with LED turnoff on service stop
- **Comprehensive logging** - Configurable log levels (DEBUG/INFO/WARNING/ERROR), systemd journal integration
- **Thread-safe** - Proper locking for concurrent access
- **Smart error handling** - Helpful messages for astronomical calculation issues

## Use Cases

### Aquarium Background Lighting
Perfect for freshwater and marine aquarium background lighting with biotope-appropriate color gradients:

- **Easy biotope switching** - Switch between Amazonian blackwater, Asian planted river, African cichlid lake, and reef environments with one click
- **Automated day/night cycles** - Schedule natural lighting transitions for your aquarium inhabitants
- **Custom gradient creation** - Design your own unique biotope lighting via Home Assistant or MQTT
- **Save favorite combinations** - Store custom gradients as presets for quick access

### Human-Centric Lighting
Automated circadian rhythm lighting with natural transitions:

- **Sunrise/sunset animations** - GPS-based astronomical calculations for accurate timing
- **Season-aware profiles** - Different color temperatures match seasonal daylight
- **Cloud simulation** - Subtle variations create realistic natural lighting

## Requirements

### Hardware
- Raspberry Pi Zero W v1 (or compatible Raspberry Pi)
- WS2813 programmable LED strip
- GPIO pin 18 connection (configurable)
- (Optional) DS18B20 temperature sensor
- Root privileges (for GPIO/DMA access)

### Software
- Python 3.9+
- MQTT broker (for Home Assistant integration)
- Tailscale (optional, for secure remote access)
- Ansible (for deployment)

## Installation

### Option 1: Automated Setup with Ansible (Recommended)

The easiest way to set up one or more Raspberry Pi devices:

```bash
# Clone repository on your local machine
git clone <your-repo-url>
cd hydrosense/ansible

# Configure MQTT password (optional)
cp group_vars/raspberry_pi/vault.yml.example group_vars/raspberry_pi/vault.yml
ansible-vault edit group_vars/raspberry_pi/vault.yml

# Test connectivity
make ping

# Run initial setup (installs everything, configures system)
make setup

# Reboot to apply boot configuration
make reboot
```

This will automatically:
- Update system packages
- Install all dependencies (Python, build tools, libraries)
- Enable SPI and 1-Wire interfaces
- Create project directories and virtual environment
- Install Python packages
- Configure and start systemd service

### Option 2: Manual Installation

For manual setup on a Raspberry Pi:

```bash
# Clone repository
git clone <your-repo-url>
cd hydrosense

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Configure environment:**
```bash
cp .env.example .env
nano .env
```

**Install systemd service:**
```bash
sudo cp hydrosense.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hydrosense
sudo systemctl start hydrosense
```

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LED_COUNT` | `30` | Number of LEDs in the strip |
| `LED_PIN` | `18` | GPIO pin number (BCM mode) |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |
| `MQTT_ENABLED` | `false` | Enable Home Assistant integration |
| `MQTT_BROKER` | `localhost` | MQTT broker hostname/IP |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` | - | MQTT username (optional) |
| `MQTT_PASSWORD` | - | MQTT password (optional) |
| `MQTT_CLIENT_ID` | `led_strip` | MQTT client identifier |
| `GRADIENT_PRESETS_FILE` | `data/gradient_presets.json` | Preset storage location |
| `TEMP_ENABLED` | `false` | Enable temperature sensors |
| `TEMP_SENSOR_IDS`| | Comma-separated list of sensor IDs (or empty for auto-discovery) |
| `TEMP_UPDATE_INTERVAL` | `60` | Seconds between temperature readings |
| `TEMP_UNIT` | `celsius` | `celsius` or `fahrenheit` |

### Ansible Configuration (`ansible/`)

- **`inventory/hosts.yml`**: Define your Raspberry Pi hosts and their specific variables (e.g., `led_count`, `mqtt_client_id`).
- **`group_vars/raspberry_pi/vault.yml`**: Store sensitive data like MQTT passwords and Tailscale auth keys. Use `ansible-vault` to edit.

## Deployment

### Using Ansible (Recommended)

Deploy code changes to your Raspberry Pi devices:

```bash
cd ansible
make deploy
```

### Using `deploy.sh` (Alternative)

For manual deployment to a single device:

```bash
./deploy.sh
```

## API Endpoints

Interactive API docs are available at `/docs` (Swagger UI) and `/redoc` on your device's IP address.

- **`POST /backlight/rgb`**: Set a solid RGB color.
- **`POST /backlight/hsv`**: Set a solid HSV color.
- **`POST /backlight/off`**: Turn off the LEDs.
- **`POST /backlight/sunrise/auto`**: Start a sunrise animation.
- **`POST /backlight/sunset/auto`**: Start a sunset animation.
- **`POST /backlight/gradient/static`**: Set a static gradient.
- **`POST /backlight/gradient/animated`**: Start an animated gradient.
- **`GET /backlight/gradient/presets`**: List available gradient presets.
- **`GET /backlight/gradient/preset/{name}`**: Apply a gradient preset.
- **`POST /backlight/gradient/preset/save`**: Save a new gradient preset.
- **`DELETE /backlight/gradient/preset/{name}`**: Delete a gradient preset.
- **`GET /backlight/state`**: Get the current state of the LEDs.
- **`GET /temperature`**: Get readings from all temperature sensors.
- **`GET /temperature/{sensor_id}`**: Get a reading from a specific temperature sensor.

## Home Assistant Integration

Complete integration guide for controlling HydroSense LED strips via Home Assistant.

### Quick Start

1. **Install MQTT Broker** (Mosquitto add-on recommended)
2. **Configure MQTT Integration** in Home Assistant
3. **Set `.env` on Raspberry Pi**:
   ```bash
   MQTT_ENABLED=true
   MQTT_BROKER=homeassistant.local
   MQTT_USERNAME=your_mqtt_user
   MQTT_PASSWORD=your_mqtt_password
   MQTT_CLIENT_ID=rpizero-01  # Unique per device
   ```
4. **Restart HydroSense**: `sudo systemctl restart hydrosense`
5. **Check HA**: Devices appear automatically!

### Auto-Discovery

HydroSense uses MQTT Discovery - devices appear automatically in Home Assistant:

- **LED Strip**: `light.led_strip_<client_id>`
  - RGB color control
  - Brightness (0-255)
  - Effects: `none`, `gradient_shift`, `gradient_pulse`, `rainbow`

- **Temperature Sensors**: `sensor.temperature_<sensor_id>`
  - Current reading (°C or °F)
  - Attributes: `valid`, `error`, `timestamp`, `celsius`, `fahrenheit`

### Dashboard Examples

#### Basic LED Control

Simple entity card:

```yaml
type: entities
title: LED Strip Control
entities:
  - entity: light.led_strip_rpizero_01
    name: LED Strip
```

#### Complete Aquarium Control Panel

Full control with temperature monitoring and preset buttons:

```yaml
type: vertical-stack
cards:
  # LED Strip Control
  - type: light
    entity: light.led_strip_rpizero_01
    name: Aquarium Backlight
    icon: mdi:led-strip-variant

  # Temperature Display
  - type: sensor
    entity: sensor.temperature_28_00000a1b2c3d
    name: Water Temperature
    icon: mdi:thermometer
    graph: line
    hours_to_show: 24

  # Biotope Presets
  - type: markdown
    content: "## 🐠 Aquarium Biotope Presets"

  - type: horizontal-stack
    cards:
      - type: button
        name: Amazonian
        icon: mdi:fish
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"amazonian"}'

      - type: button
        name: Asian River
        icon: mdi:bridge
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"asian_river"}'

  - type: horizontal-stack
    cards:
      - type: button
        name: African Lake
        icon: mdi:water
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"african_lake"}'

      - type: button
        name: Reef
        icon: mdi:coral
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"reef"}'

  # General Presets
  - type: markdown
    content: "## 🌈 General Presets"

  - type: horizontal-stack
    cards:
      - type: button
        name: Sunset
        icon: mdi:weather-sunset
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"sunset"}'

      - type: button
        name: Ocean
        icon: mdi:waves
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"ocean"}'

      - type: button
        name: Fire
        icon: mdi:fire
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"fire"}'

  # Moonlight Mode
  - type: button
    name: 🌙 Moonlight Mode
    icon: mdi:moon-waxing-crescent
    tap_action:
      action: call-service
      service: mqtt.publish
      data:
        topic: hydrosense/rpizero-01/gradient/command
        payload: '{"type":"gradient","action":"load_preset","preset_name":"moonlight"}'
```

### Automations

#### Automatic Day/Night Cycle

```yaml
automation:
  - alias: "Aquarium Lights - Sunrise"
    trigger:
      - platform: sun
        event: sunrise
        offset: "-00:30:00"
    action:
      - service: mqtt.publish
        data:
          topic: hydrosense/rpizero-01/gradient/command
          payload: '{"type":"gradient","action":"load_preset","preset_name":"amazonian"}'

  - alias: "Aquarium Lights - Sunset"
    trigger:
      - platform: sun
        event: sunset
        offset: "+00:30:00"
    action:
      - service: light.turn_off
        target:
          entity_id: light.led_strip_rpizero_01
```

#### Temperature Alert

```yaml
automation:
  - alias: "Aquarium Temperature Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.temperature_28_00000a1b2c3d
        above: 28
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Aquarium Temperature High"
          message: "Water temperature is {{ states('sensor.temperature_28_00000a1b2c3d') }}°C"
      - service: light.turn_on
        target:
          entity_id: light.led_strip_rpizero_01
        data:
          rgb_color: [255, 0, 0]
          brightness: 255
```

### Advanced MQTT Control

#### Custom Static Gradient

```yaml
service: mqtt.publish
data:
  topic: hydrosense/rpizero-01/gradient/command
  payload: >
    {
      "type": "gradient",
      "action": "static",
      "config": {
        "stops": [
          {"position": 0.0, "r": 255, "g": 0, "b": 0},
          {"position": 1.0, "r": 0, "g": 0, "b": 255}
        ],
        "brightness": 0.8
      }
    }
```

#### Animated Gradient

```yaml
service: mqtt.publish
data:
  topic: hydrosense/rpizero-01/gradient/command
  payload: >
    {
      "type": "gradient",
      "action": "animated",
      "duration": 300,
      "config": {
        "stops": [
          {"position": 0.0, "r": 255, "g": 100, "b": 0},
          {"position": 1.0, "r": 138, "g": 43, "b": 226}
        ],
        "brightness": 1.0,
        "animation": "shift",
        "speed": 1.5,
        "direction": "forward"
      }
    }
```

**Animation types**: `shift` (scrolling), `pulse` (breathing), `rainbow` (hue rotation)

### Multiple Devices

For multiple HydroSense devices, ensure each has a unique `MQTT_CLIENT_ID`:

```yaml
# Device 1: rpizero-01
# Device 2: rpizero-02
# Device 3: rpi3-rnd-01
```

Example multi-device dashboard:

```yaml
type: vertical-stack
title: All LED Strips
cards:
  - type: entities
    title: Aquarium
    entities:
      - light.led_strip_rpizero_01
      - sensor.temperature_28_00000a1b2c3d

  - type: entities
    title: Living Room
    entities:
      - light.led_strip_rpizero_02

  - type: button
    name: All Off
    icon: mdi:lightbulb-group-off
    tap_action:
      action: call-service
      service: light.turn_off
      target:
        entity_id:
          - light.led_strip_rpizero_01
          - light.led_strip_rpizero_02
```

### MQTT Topic Reference

For device with `MQTT_CLIENT_ID=rpizero-01`:

| Topic | Direction | Description |
|-------|-----------|-------------|
| `homeassistant/light/rpizero-01/config` | → HA | Auto-discovery config |
| `homeassistant/light/rpizero-01/state` | → HA | Current LED state |
| `homeassistant/light/rpizero-01/command` | HA → | Commands from HA |
| `hydrosense/rpizero-01/gradient/command` | HA → | Custom gradients |
| `hydrosense/rpizero-01/availability` | → HA | online/offline |
| `hydrosense/rpizero-01/temperature/<sensor_id>/state` | → HA | Temperature data |

### Troubleshooting HA Integration

**Devices not appearing:**
1. Check MQTT integration is connected
2. Verify `.env` has correct broker IP
3. Check logs: `sudo journalctl -u hydrosense -f`
4. Restart: `sudo systemctl restart hydrosense`

**Temperature sensors not updating:**
1. Check sensor detection: `ls /sys/bus/w1/devices/`
2. Should see sensors starting with `28-`
3. Test API: `curl http://rpizero-01:8000/temperature`

**MQTT commands not working:**
1. Verify `MQTT_CLIENT_ID` matches in commands
2. Validate JSON payload
3. Monitor MQTT: `mosquitto_sub -h <broker> -t 'hydrosense/#' -v`

## Hardware Setup

### DS18B20 Temperature Sensor

1.  **Wiring**: Connect the DS18B20 sensor to GPIO 4, 3.3V, and GND. A 4.7kΩ pull-up resistor is required between the data line and 3.3V.
2.  **Enable 1-Wire**: Add `dtoverlay=w1-gpio` to `/boot/config.txt`. The Ansible `setup` playbook does this automatically.
3.  **Test**: Check for your sensor in `/sys/bus/w1/devices/`. It should start with `28-`.
4.  **Configure HydroSense**: Set `TEMP_ENABLED=true` in your `.env` file. Leave `TEMP_SENSOR_IDS` blank for auto-discovery.

## Development

### Running Locally

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with auto-reload (development)
sudo -E $(which python) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload
```

### Architecture

The application's main components are in the `app/` directory. `main.py` is the FastAPI entry point, `led.py` handles hardware control, `mqtt_client.py` manages Home Assistant integration, and `animations.py` and `gradient.py` contain the lighting logic.

### Testing

The project includes a comprehensive test suite covering all major components:

**Test Coverage:**
- **Unit Tests**: Core logic (state management, gradient rendering, color math)
- **Integration Tests**: API endpoints, animations, MQTT integration
- **Hardware Mocking**: Tests run on any platform without Raspberry Pi hardware

**Running Tests:**

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
make test
# or
pytest

# Run with coverage report
make test-coverage

# Run specific test file
pytest tests/test_gradient.py

# Run specific test
pytest tests/test_api.py::TestRGBEndpoint::test_set_rgb_valid
```

**Test Files:**
- `test_lighting_math.py` - Mathematical helpers (smoothstep, lerp, noise)
- `test_state.py` - LED state management and thread safety
- `test_gradient.py` - Gradient rendering and validation
- `test_config.py` - Configuration loading and environment variables
- `test_led.py` - LED hardware abstraction (with mocks)
- `test_animations.py` - Sunrise/sunset animations (with mocks)
- `test_gradient_presets.py` - Preset storage and management
- `test_api.py` - FastAPI endpoints (with TestClient)

**Coverage Report:**

After running `make test-coverage`, open `htmlcov/index.html` in your browser to see detailed coverage information.

**CI/CD Integration:**

Tests can be integrated into CI/CD pipelines. All tests use mocked hardware and run without physical Raspberry Pi.

### Tailscale

For secure remote access, Tailscale can be set up using Ansible. You can use a reusable auth key stored in the Ansible vault for automatic setup, or authenticate manually.

## Troubleshooting

- **Service won't start**: Check `journalctl -u hydrosense` for errors. Permission errors often relate to GPIO/DMA access. The systemd service must run as root.
- **MQTT not connecting**: Verify broker, port, and credentials in your `.env` file. Use `mosquitto_sub` to test the connection.
- **LEDs not appearing in Home Assistant**: Ensure MQTT is enabled and the integration is set up in HA. Check for discovery messages on the `homeassistant/light/.../config` topic.

## Changelog Summary (2026-01-01)

- **Security**: Added `.gitignore` for `ansible`, fixed vault loading, and improved `systemd` service permissions.
- **MQTT**: Implemented unique MQTT topics per device to prevent Home Assistant conflicts.
- **Tailscale**: Improved manual and automatic authentication processes.
- **Deployment**: Fixed file synchronization in the Ansible `deploy` playbook.

## License

MIT

## Contributing

Pull requests are welcome!