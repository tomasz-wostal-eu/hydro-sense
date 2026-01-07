# Home Assistant Integration

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

#### Complete Dashboard with Water Level & Pump Control

Comprehensive control panel with all HydroSense features including water monitoring and automation:

```yaml
type: vertical-stack
title: 🐠 HydroSense Aquarium Control
cards:
  # Status Overview
  - type: horizontal-stack
    cards:
      # Water Level Status
      - type: custom:mushroom-entity-card
        entity: binary_sensor.water_level_rpizero_01
        name: Water Level
        icon: mdi:waves
        icon_color: >
          {% if is_state('binary_sensor.water_level_rpizero_01', 'on') %}
            green
          {% else %}
            red
          {% endif %}
        tap_action:
          action: more-info

      # Pump Status
      - type: custom:mushroom-entity-card
        entity: switch.pump
        name: Pump
        icon: mdi:pump
        icon_color: >
          {% if is_state('switch.pump', 'on') %}
            blue
          {% else %}
            grey
          {% endif %}
        tap_action:
          action: toggle

      # Temperature
      - type: custom:mushroom-entity-card
        entity: sensor.temperature_28_00000a1b2c3d
        name: Temperature
        icon: mdi:thermometer
        icon_color: >
          {% set temp = states('sensor.temperature_28_00000a1b2c3d') | float %}
          {% if temp > 28 %}
            red
          {% elif temp > 26 %}
            orange
          {% elif temp > 24 %}
            green
          {% else %}
            blue
          {% endif %}

  # LED Strip Control
  - type: light
    entity: light.led_strip_rpizero_01
    name: Aquarium Backlight
    icon: mdi:led-strip-variant

  # Pump Automation Controls
  - type: entities
    title: 💧 Pump Automation
    entities:
      - type: custom:multiple-entity-row
        entity: switch.pump
        name: Pump
        icon: mdi:pump
        state_header: Status
        toggle: true
        entities:
          - entity: sensor.pump_mode_rpizero_01
            name: Mode
          - entity: sensor.pump_runtime_rpizero_01
            name: Runtime

      - type: buttons
        entities:
          - entity: button.pump_mode_auto_rpizero_01
            name: AUTO
            icon: mdi:auto-fix
            tap_action:
              action: call-service
              service: rest_command.pump_automation_mode
              data:
                mode: AUTO

          - entity: button.pump_mode_manual_rpizero_01
            name: MANUAL
            icon: mdi:hand-back-right
            tap_action:
              action: call-service
              service: rest_command.pump_automation_mode
              data:
                mode: MANUAL

          - entity: button.pump_mode_disabled_rpizero_01
            name: DISABLE
            icon: mdi:stop-circle
            tap_action:
              action: call-service
              service: rest_command.pump_automation_mode
              data:
                mode: DISABLED

  # Water Level Details
  - type: entities
    title: 🌊 Water Level Sensor
    entities:
      - entity: binary_sensor.water_level_rpizero_01
        name: Status
        icon: mdi:waves
      - type: attribute
        entity: binary_sensor.water_level_rpizero_01
        attribute: last_change
        name: Last Change
      - type: attribute
        entity: binary_sensor.water_level_rpizero_01
        attribute: gpio_state
        name: GPIO State
      - type: attribute
        entity: binary_sensor.water_level_rpizero_01
        attribute: gpio_pin
        name: GPIO Pin

  # Temperature Graph
  - type: sensor
    entity: sensor.temperature_28_00000a1b2c3d
    name: Water Temperature (24h)
    icon: mdi:thermometer
    graph: line
    hours_to_show: 24
    detail: 2

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

      - type: button
        name: African Lake
        icon: mdi:water
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"african_lake"}'

  - type: horizontal-stack
    cards:
      - type: button
        name: Reef
        icon: mdi:coral
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"reef"}'

      - type: button
        name: Moonlight
        icon: mdi:moon-waxing-crescent
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"moonlight"}'

      - type: button
        name: Sunset
        icon: mdi:weather-sunset
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"sunset"}'
```

**Required Home Assistant Configuration:**

**NOTE:** Water level sensor and relay switch are **auto-discovered via MQTT** - they will appear automatically in Home Assistant. You only need to add the configuration below for REST commands and template sensors.

Add these to your `configuration.yaml`:

```yaml
rest_command:
  # Pump automation mode control
  pump_automation_mode:
    url: "http://192.168.55.144:8000/pump-automation/mode"
    method: POST
    content_type: "application/json"
    payload: '{"mode": "{{ mode }}"}'

# Template sensors for pump automation status
template:
  - sensor:
      - name: "Pump Mode rpizero-01"
        unique_id: pump_mode_rpizero_01
        state: >
          {% set data = state_attr('sensor.pump_automation_rpizero_01', 'mode') %}
          {{ data if data else 'unknown' }}
        icon: mdi:cog

      - name: "Pump Runtime rpizero-01"
        unique_id: pump_runtime_rpizero_01
        state: >
          {% set runtime = state_attr('sensor.pump_automation_rpizero_01', 'total_runtime_seconds') %}
          {{ (runtime | float / 60) | round(1) if runtime else 0 }}
        unit_of_measurement: "min"
        icon: mdi:timer

# Manual MQTT configuration (ONLY needed if auto-discovery is disabled)
# Water level and relay are auto-discovered by default - no manual config needed!
# The following is optional and only for reference:
mqtt:
  sensor:
    # Pump automation status (manual config - auto-discovery not yet implemented for this)
    - name: "Pump Automation rpizero-01"
      unique_id: pump_automation_rpizero_01
      state_topic: "hydrosense/rpizero-01/pump_automation/state"
      value_template: "{{ value_json.mode }}"
      json_attributes_topic: "hydrosense/rpizero-01/pump_automation/state"
      icon: mdi:cog-sync
      availability:
        - topic: "hydrosense/rpizero-01/availability"
          payload_available: "online"
          payload_not_available: "offline"
```

**Optional: Custom Mushroom Cards**

For the best UI experience, install these custom cards via HACS:
- [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) - Modern, clean card designs
- [Multiple Entity Row](https://github.com/benct/lovelace-multiple-entity-row) - Compact entity rows

**Alternative: Without Custom Cards**

If you don't want to install custom cards, use this standard configuration:

```yaml
type: vertical-stack
title: 🐠 HydroSense Aquarium Control
cards:
  # Status Overview
  - type: glance
    title: System Status
    entities:
      - entity: binary_sensor.water_level_rpizero_01
        name: Water Level
      - entity: switch.pump
        name: Pump
      - entity: sensor.temperature_28_00000a1b2c3d
        name: Temperature
      - entity: light.led_strip_rpizero_01
        name: LED Strip

  # LED Control
  - type: light
    entity: light.led_strip_rpizero_01
    name: Aquarium Backlight

  # Pump Controls
  - type: entities
    title: Pump Automation
    entities:
      - entity: switch.pump
        name: Pump
      - entity: sensor.pump_mode_rpizero_01
        name: Current Mode
      - entity: sensor.pump_runtime_rpizero_01
        name: Total Runtime (min)

  # Mode Controls
  - type: horizontal-stack
    cards:
      - type: button
        name: AUTO Mode
        icon: mdi:auto-fix
        tap_action:
          action: call-service
          service: rest_command.pump_automation_mode
          data:
            mode: AUTO

      - type: button
        name: MANUAL Mode
        icon: mdi:hand-back-right
        tap_action:
          action: call-service
          service: rest_command.pump_automation_mode
          data:
            mode: MANUAL

      - type: button
        name: DISABLE
        icon: mdi:stop-circle
        tap_action:
          action: call-service
          service: rest_command.pump_automation_mode
          data:
            mode: DISABLED

  # Water Level Details
  - type: entities
    title: Water Level Sensor
    entities:
      - binary_sensor.water_level_rpizero_01

  # Temperature Graph
  - type: sensor
    entity: sensor.temperature_28_00000a1b2c3d
    graph: line
    hours_to_show: 24

  # Biotope Presets (same as before)
  - type: grid
    columns: 3
    square: false
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
      - type: button
        name: Moonlight
        icon: mdi:moon-waxing-crescent
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"moonlight"}'
      - type: button
        name: Sunset
        icon: mdi:weather-sunset
        tap_action:
          action: call-service
          service: mqtt.publish
          data:
            topic: hydrosense/rpizero-01/gradient/command
            payload: '{"type":"gradient","action":"load_preset","preset_name":"sunset"}'
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

#### Water Level & Pump Automations

**IMPORTANT:**
- Copy only the automation entries you need (without the `automation:` header if you already have other automations in your `configuration.yaml`). If this is your first automation, copy the entire block including `automation:`.
- **`notify.mobile_app`** requires the Home Assistant mobile app. Replace with `notify.notify` or remove notification actions if you don't have the mobile app configured.
- These automations use auto-discovered entities: `binary_sensor.water_level_rpizero_01`, `switch.pump`, and `light.led_strip_rpizero_01`

Complete set of water level monitoring and pump control automations:

```yaml
automation:
  # ============================================================================
  # Water Level Alerts
  # ============================================================================

  - alias: "Aquarium Water Level Low Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.water_level_rpizero_01
        to: 'off'
        for:
          seconds: 5
    action:
      - service: notify.mobile_app
        data:
          title: "💧 Aquarium Water Level Low"
          message: "Water level is below sensor. Check aquarium and refill if needed."
      - service: light.turn_on
        target:
          entity_id: light.led_strip_rpizero_01
        data:
          rgb_color: [255, 0, 0]
          brightness: 128

  - alias: "Aquarium Water Level Restored"
    trigger:
      - platform: state
        entity_id: binary_sensor.water_level_rpizero_01
        to: 'on'
        for:
          seconds: 5
    action:
      - service: notify.mobile_app
        data:
          title: "✅ Aquarium Water Level OK"
          message: "Water level has been restored."
      - service: mqtt.publish
        data:
          topic: hydrosense/rpizero-01/gradient/command
          payload: '{"type":"gradient","action":"load_preset","preset_name":"amazonian"}'

  # ============================================================================
  # Auto-Fill with Pump (Advanced)
  # ============================================================================

  - alias: "Aquarium Auto-Fill - Start Pump"
    trigger:
      - platform: state
        entity_id: binary_sensor.water_level_rpizero_01
        to: 'off'  # Water level LOW
        for:
          seconds: 10
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.pump
      - service: notify.mobile_app
        data:
          title: "💧 Auto-Fill Started"
          message: "Pump activated to refill aquarium"

  - alias: "Aquarium Auto-Fill - Stop Pump"
    trigger:
      - platform: state
        entity_id: binary_sensor.water_level_rpizero_01
        to: 'on'  # Water level OK
        for:
          seconds: 3
    condition:
      - condition: state
        entity_id: switch.pump
        state: 'on'
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.pump
      - service: notify.mobile_app
        data:
          title: "✅ Auto-Fill Complete"
          message: "Water level OK, pump stopped"

  - alias: "Pump Safety - Max Runtime Exceeded"
    trigger:
      - platform: state
        entity_id: switch.pump
        to: 'on'
        for:
          minutes: 5
    condition:
      - condition: state
        entity_id: binary_sensor.water_level_rpizero_01
        state: 'off'
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.pump
      - service: notify.mobile_app
        data:
          title: "🚨 PUMP SAFETY ALERT"
          message: "Pump ran for 5 minutes but water level still low. Possible leak or pump failure."
          data:
            tag: "pump_safety_alert"
            priority: high
            ttl: 0

  # ============================================================================
  # Scheduled Water Changes
  # ============================================================================

  - alias: "Weekly Water Change Reminder"
    trigger:
      - platform: time
        at: "10:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: notify.mobile_app
        data:
          title: "🐠 Weekly Water Change"
          message: "Time for weekly 25% water change"
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
