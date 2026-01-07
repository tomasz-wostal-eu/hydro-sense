# HydroSense

FastAPI-based human-centric lighting control for Raspberry Pi Zero W with WS2813 LED strips.

**NEW:** Full Home Assistant integration via MQTT with bidirectional sync!
**NEW:** Aquarium biotope presets (Amazonian, Asian River, African Lake, Reef)
**NEW:** Ansible automation for easy setup and deployment
**NEW:** DS18B20 temperature sensor support
**NEW:** Water level monitoring with conductive sensors
**NEW:** Relay control for pumps and other equipment
**NEW:** Automatic pump control based on water level

## Documentation

- [Features](#features)
- [Use Cases](#use-cases)
- [Hardware & Software Requirements](#requirements)
- [Installation](docs/INSTALL.md)
- [Configuration](docs/CONFIGURATION.md)
- [Deployment](docs/DEPLOYMENT.md)
- [API Endpoints](docs/API.md)
- [Hardware Setup](docs/HARDWARE.md)
- [Home Assistant Integration](docs/HOME_ASSISTANT.md)
- [Development](docs/DEVELOPMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

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
- **Temperature Sensing** - Support for DS18B20 temperature sensors
- **Water Level Monitoring** - Conductive sensor support for aquarium water level detection
- **Relay Control** - GPIO-based relay switching for pumps, filters, and other equipment
- **Pump Automation** - Automatic water level management with configurable intervals and safety features

### Home Assistant Integration
- **MQTT bidirectional sync** - Control LEDs, relays, and pumps from HA with real-time state updates
- **Auto-discovery** - Automatically appears as `light.led_strip`, `sensor.temperature_*`, `switch.*` in Home Assistant
- **Full feature support** - RGB colors, brightness, effects (rainbow, gradient shift/pulse), relay control
- **State retention** - HA remembers device states across restarts (MQTT retained messages)
- **Availability tracking** - Shows online/offline status in HA
- **Unified device** - All entities grouped under single HydroSense device

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
- (Optional) Conductive water level sensor (2-wire)
- (Optional) Relay module for pump/equipment control
- Root privileges (for GPIO/DMA access)

### Software
- Python 3.9+
- MQTT broker (for Home Assistant integration)
- Tailscale (optional, for secure remote access)
- Ansible (for deployment)

## License

MIT

## Contributing

Pull requests are welcome!
