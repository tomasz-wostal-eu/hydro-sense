# Configuration

HydroSense can be configured using environment variables or via Ansible for automated setups.

## Environment Variables (`.env`)

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
| `RELAY_ENABLED` | `false` | Enable relay control |
| `RELAY_CONFIG` | | Relay configuration (format: `id:name:pin:active_low:default:max_time`) |
| `WATER_LEVEL_ENABLED` | `false` | Enable water level sensor |
| `WATER_LEVEL_PIN` | `23` | GPIO pin for water level sensor |
| `WATER_LEVEL_ACTIVE_HIGH` | `true` | `true` if HIGH = water low, `false` if LOW = water low |
| `WATER_LEVEL_DEBOUNCE_TIME` | `0.5` | Debounce time in seconds |
| `PUMP_AUTOMATION_ENABLED` | `false` | Enable automatic pump control |
| `PUMP_RELAY_ID` | `pump` | Relay ID to control |
| `PUMP_ON_INTERVAL` | `30` | Seconds to run pump when water low |
| `PUMP_OFF_INTERVAL` | `30` | Seconds to wait between pump cycles |
| `PUMP_MAX_RUNTIME` | `300` | Maximum total pump runtime in seconds (safety limit) |

## Ansible Configuration (`ansible/`)

- **`inventory/hosts.yml`**: Define your Raspberry Pi hosts and their specific variables (e.g., `led_count`, `mqtt_client_id`).
- **`group_vars/raspberry_pi/vault.yml`**: Store sensitive data like MQTT passwords and Tailscale auth keys. Use `ansible-vault` to edit.
