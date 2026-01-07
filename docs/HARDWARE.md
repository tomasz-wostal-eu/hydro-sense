# Hardware Setup

## DS18B20 Temperature Sensor

1.  **Wiring**: Connect the DS18B20 sensor to GPIO 4, 3.3V, and GND. A 4.7kΩ pull-up resistor is required between the data line and 3.3V.
2.  **Enable 1-Wire**: Add `dtoverlay=w1-gpio` to `/boot/config.txt`. The Ansible `setup` playbook does this automatically.
3.  **Test**: Check for your sensor in `/sys/bus/w1/devices/`. It should start with `28-`.
4.  **Configure HydroSense**: Set `TEMP_ENABLED=true` in your `.env` file. Leave `TEMP_SENSOR_IDS` blank for auto-discovery.

## Water Level Monitoring & Pump Automation

HydroSense includes comprehensive water level monitoring and automatic pump control for aquarium water management.

### Hardware Setup

#### Water Level Sensor (Conductive)

**Wiring:**
1. **Wire 1**: Connect to GPIO 23 (configurable via `WATER_LEVEL_PIN`)
2. **Wire 2**: Connect to GND

**How it works:**
- Sensor wires submerged in water → conducts → GPIO reads LOW → **Water OK**
- Sensor wires above water → no conduction → pull-up resistor → GPIO reads HIGH → **Water LOW**

**Important:** The code uses a pull-UP resistor configuration. When the sensor is disconnected or above water, GPIO reads HIGH, correctly indicating low water level.

#### Relay Module

**Wiring:**
1. **VCC**: Connect to 5V or 3.3V (check your relay module specs)
2. **GND**: Connect to GND
3. **IN/Signal**: Connect to GPIO 17 (configurable via `RELAY_CONFIG`)
4. **COM/NO/NC**: Connect your pump/equipment

**Relay Configuration:**
- Most relay modules are **active-LOW** (signal LOW = relay ON)
- Set `active_low: true` in configuration for these modules
- HydroSense supports multiple relays with individual GPIO pins

### Configuration

**Example `.env` configuration:**

```bash
# Water Level Sensor
WATER_LEVEL_ENABLED=true
WATER_LEVEL_PIN=23
WATER_LEVEL_ACTIVE_HIGH=true  # HIGH = water low (for conductive sensors with pull-up)
WATER_LEVEL_DEBOUNCE_TIME=0.5  # Prevents false triggers

# Relay Control
RELAY_ENABLED=true
RELAY_CONFIG=pump:Aquarium Pump:17:true:OFF:60
# Format: id:name:gpio_pin:active_low:default_state:max_on_time_seconds

# Pump Automation
PUMP_AUTOMATION_ENABLED=true
PUMP_RELAY_ID=pump
PUMP_ON_INTERVAL=30    # Run pump for 30 seconds
PUMP_OFF_INTERVAL=30   # Wait 30 seconds between cycles
PUMP_MAX_RUNTIME=300   # Maximum 5 minutes total runtime (safety)
```

**Ansible Configuration (inventory/hosts.yml):**

```yaml
rpizero-01:
  ansible_host: 192.168.1.100
  # ... other config ...

  # Water level sensor
  water_level_enabled: true
  water_level_pin: 23
  water_level_active_high: true
  water_level_debounce_time: 0.5

  # Relay
  relay_enabled: true
  relay_config: "pump:Aquarium Pump:17:true:OFF:60"

  # Pump automation
  pump_automation_enabled: true
  pump_relay_id: "pump"
  pump_on_interval: 30
  pump_off_interval: 30
  pump_max_runtime: 300
```

### Usage

#### Manual Control

```bash
# Check water level status
curl http://rpizero-01:8000/water-level

# Turn pump on manually
curl -X POST http://rpizero-01:8000/relay/pump/on

# Turn pump off manually
curl -X POST http://rpizero-01:8000/relay/pump/off

# Check pump automation status
curl http://rpizero-01:8000/pump-automation
```

#### Automatic Mode

When `PUMP_AUTOMATION_ENABLED=true` and mode is set to AUTO:

1. **Water level OK** → Pump stays off, system monitors water level
2. **Water level LOW detected** → Pump turns ON for `PUMP_ON_INTERVAL` seconds
3. **Pump turns OFF** → Waits `PUMP_OFF_INTERVAL` seconds
4. **Check water level** → If still low, repeat cycle
5. **Safety limit** → If total runtime exceeds `PUMP_MAX_RUNTIME`, automation stops

**Set automation mode:**

```bash
# Enable automatic control
curl -X POST http://rpizero-01:8000/pump-automation/mode \
  -H 'Content-Type: application/json' \
  -d '{"mode":"AUTO"}'

# Manual control (automation monitors but doesn't control pump)
curl -X POST http://rpizero-01:8000/pump-automation/mode \
  -H 'Content-Type: application/json' \
  -d '{"mode":"MANUAL"}'

# Disable automation completely
curl -X POST http://rpizero-01:8000/pump-automation/mode \
  -H 'Content-Type: application/json' \
  -d '{"mode":"DISABLED"}'
```

### Safety Features

- **Auto-shutoff timer**: Relays automatically turn off after `max_on_time` seconds (default: 60s)
- **Maximum runtime protection**: Pump automation stops if total runtime exceeds `PUMP_MAX_RUNTIME`
- **Watchdog monitoring**: Optional relay watchdog checks relay states periodically
- **Debouncing**: Water level sensor uses debouncing to prevent false triggers from splashing
- **Thread-safe**: All relay operations use proper locking for concurrent access

### Testing

**Test water level sensor:**

```bash
# Sensor disconnected or above water - should show LOW
curl http://rpizero-01:8000/water-level
# Output: {"current_level":"LOW","gpio_state":true}

# Short the sensor wires or submerge in water - should show OK
curl http://rpizero-01:8000/water-level
# Output: {"current_level":"OK","gpio_state":false}
```

**Test relay:**

```bash
# Turn pump on (should hear relay click)
curl -X POST http://rpizero-01:8000/relay/pump/on

# Wait 5 seconds, check it's still on
sleep 5 && curl http://rpizero-01:8000/relay

# Turn pump off
curl -X POST http://rpizero-01:8000/relay/pump/off
```
