"""
MQTT client for Home Assistant integration.

Features:
- Auto-discovery (HA MQTT Discovery protocol)
- Bidirectional communication (commands + state publishing)
- Auto-reconnection on connection loss
- Last Will and Testament (LWT) for availability
- Gradient control through MQTT
"""

import asyncio
import json
import threading
from typing import Optional, Callable
from contextlib import AsyncExitStack

import aiomqtt
from app.config import (
    MQTT_ENABLED,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_CLIENT_ID,
    TEMP_UNIT,
)
from app.logger import logger
from app.state import led_state


# ============================================================================
# MQTT Topics (unique per device using MQTT_CLIENT_ID)
# ============================================================================

TOPIC_HA_CONFIG = f"homeassistant/light/{MQTT_CLIENT_ID}/config"
TOPIC_HA_STATE = f"homeassistant/light/{MQTT_CLIENT_ID}/state"
TOPIC_HA_COMMAND = f"homeassistant/light/{MQTT_CLIENT_ID}/command"

TOPIC_GRADIENT_CONFIG = f"hydrosense/{MQTT_CLIENT_ID}/gradient/config"
TOPIC_GRADIENT_COMMAND = f"hydrosense/{MQTT_CLIENT_ID}/gradient/command"
TOPIC_GRADIENT_STATE = f"hydrosense/{MQTT_CLIENT_ID}/gradient/state"

TOPIC_AVAILABILITY = f"hydrosense/{MQTT_CLIENT_ID}/availability"


# ============================================================================
# Home Assistant Discovery Config
# ============================================================================

def get_ha_discovery_config() -> dict:
    """
    Generate Home Assistant MQTT Discovery configuration.

    Returns:
        dict: HA discovery message payload

    Docs: https://www.home-assistant.io/integrations/light.mqtt/
    """
    # Create friendly name from client_id (e.g., "led-stripe" -> "LED Stripe")
    friendly_name = MQTT_CLIENT_ID.replace("-", " ").replace("_", " ").title()

    return {
        "name": f"LED Strip ({friendly_name})",
        "unique_id": f"led_strip_{MQTT_CLIENT_ID}",
        "state_topic": TOPIC_HA_STATE,
        "command_topic": TOPIC_HA_COMMAND,
        "availability_topic": TOPIC_AVAILABILITY,
        "schema": "json",
        "brightness": True,
        "brightness_scale": 255,
        "supported_color_modes": ["rgb"],
        "effect": True,
        "effect_list": ["none", "gradient_shift", "gradient_pulse", "rainbow"],
        "optimistic": False,
        "qos": 1,
        "retain": True,
        "device": {
            "identifiers": [f"hydrosense_{MQTT_CLIENT_ID}"],
            "name": f"HydroSense {MQTT_CLIENT_ID}",
            "model": "Raspberry Pi LED Controller",
            "manufacturer": "HydroSense"
        }
    }


def get_temp_sensor_discovery_config(sensor_id: str) -> dict:
    """
    Generate Home Assistant MQTT Discovery config for temperature sensor.

    Args:
        sensor_id: DS18B20 sensor ID (e.g., '28-00000xxxxx')

    Returns:
        dict: HA discovery message payload for temperature sensor

    Docs: https://www.home-assistant.io/integrations/sensor.mqtt/
    """
    # Create friendly name from sensor_id
    friendly_name = sensor_id.replace("-", " ").replace("_", " ").title()

    return {
        "name": f"Temperature {friendly_name}",
        "unique_id": f"temp_{MQTT_CLIENT_ID}_{sensor_id}",
        "state_topic": f"hydrosense/{MQTT_CLIENT_ID}/temperature/{sensor_id}/state",
        "unit_of_measurement": "°C" if TEMP_UNIT == "celsius" else "°F",
        "device_class": "temperature",
        "state_class": "measurement",
        "availability_topic": TOPIC_AVAILABILITY,
        "value_template": "{{ value_json.temperature }}",
        "json_attributes_topic": f"hydrosense/{MQTT_CLIENT_ID}/temperature/{sensor_id}/state",
        "qos": 1,
        "retain": True,
        "device": {
            "identifiers": [f"hydrosense_{MQTT_CLIENT_ID}"],
            "name": f"HydroSense {MQTT_CLIENT_ID}",
            "model": "Raspberry Pi LED Controller",
            "manufacturer": "HydroSense"
        }
    }


def get_relay_discovery_config(relay_id: str, relay_name: str) -> dict:
    """
    Generate Home Assistant MQTT Discovery config for relay switch.

    Args:
        relay_id: Relay identifier (e.g., 'pump', 'heater')
        relay_name: Human-readable relay name (e.g., 'Aquarium Pump')

    Returns:
        dict: HA discovery message payload for switch

    Docs: https://www.home-assistant.io/integrations/switch.mqtt/
    """
    return {
        "name": relay_name,
        "unique_id": f"relay_{MQTT_CLIENT_ID}_{relay_id}",
        "state_topic": f"homeassistant/switch/{relay_id}/state",
        "command_topic": f"homeassistant/switch/{relay_id}/set",
        "availability_topic": TOPIC_AVAILABILITY,
        "payload_on": "ON",
        "payload_off": "OFF",
        "state_on": "ON",
        "state_off": "OFF",
        "optimistic": False,
        "qos": 1,
        "retain": True,
        "device": {
            "identifiers": [f"hydrosense_{MQTT_CLIENT_ID}"],
            "name": f"HydroSense {MQTT_CLIENT_ID}",
            "model": "Raspberry Pi LED Controller",
            "manufacturer": "HydroSense"
        }
    }


def get_water_level_discovery_config() -> dict:
    """
    Generate Home Assistant MQTT Discovery config for water level sensor.

    Returns:
        dict: HA discovery message payload for binary_sensor

    Docs: https://www.home-assistant.io/integrations/binary_sensor.mqtt/
    """
    return {
        "name": f"Water Level",
        "unique_id": f"water_level_{MQTT_CLIENT_ID}",
        "state_topic": f"hydrosense/{MQTT_CLIENT_ID}/water_level/state",
        "availability_topic": TOPIC_AVAILABILITY,
        "payload_on": "OK",
        "payload_off": "LOW",
        "device_class": "moisture",
        "qos": 1,
        "retain": True,
        "json_attributes_topic": f"hydrosense/{MQTT_CLIENT_ID}/water_level/state",
        "value_template": "{{ value_json.current_level }}",
        "device": {
            "identifiers": [f"hydrosense_{MQTT_CLIENT_ID}"],
            "name": f"HydroSense {MQTT_CLIENT_ID}",
            "model": "Raspberry Pi LED Controller",
            "manufacturer": "HydroSense"
        }
    }


def get_pump_mode_sensor_discovery_config() -> dict:
    """
    Generate Home Assistant MQTT Discovery config for pump mode sensor.

    Returns:
        dict: HA discovery message payload for sensor

    Docs: https://www.home-assistant.io/integrations/sensor.mqtt/
    """
    return {
        "name": f"Pump Mode",
        "unique_id": f"pump_mode_{MQTT_CLIENT_ID}",
        "state_topic": f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/state",
        "availability_topic": TOPIC_AVAILABILITY,
        "value_template": "{{ value_json.mode }}",
        "icon": "mdi:cog",
        "qos": 1,
        "retain": True,
        "json_attributes_topic": f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/state",
        "device": {
            "identifiers": [f"hydrosense_{MQTT_CLIENT_ID}"],
            "name": f"HydroSense {MQTT_CLIENT_ID}",
            "model": "Raspberry Pi LED Controller",
            "manufacturer": "HydroSense"
        }
    }


def get_pump_runtime_sensor_discovery_config() -> dict:
    """
    Generate Home Assistant MQTT Discovery config for pump runtime sensor.

    Returns:
        dict: HA discovery message payload for sensor

    Docs: https://www.home-assistant.io/integrations/sensor.mqtt/
    """
    return {
        "name": f"Pump Runtime",
        "unique_id": f"pump_runtime_{MQTT_CLIENT_ID}",
        "state_topic": f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/state",
        "availability_topic": TOPIC_AVAILABILITY,
        "value_template": "{{ value_json.total_runtime | round(1) }}",
        "unit_of_measurement": "s",
        "icon": "mdi:timer",
        "state_class": "total_increasing",
        "qos": 1,
        "retain": True,
        "json_attributes_topic": f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/state",
        "device": {
            "identifiers": [f"hydrosense_{MQTT_CLIENT_ID}"],
            "name": f"HydroSense {MQTT_CLIENT_ID}",
            "model": "Raspberry Pi LED Controller",
            "manufacturer": "HydroSense"
        }
    }


def get_pump_mode_button_discovery_config(mode: str) -> dict:
    """
    Generate Home Assistant MQTT Discovery config for pump mode button.

    Args:
        mode: Automation mode (AUTO, MANUAL, DISABLED)

    Returns:
        dict: HA discovery message payload for button

    Docs: https://www.home-assistant.io/integrations/button.mqtt/
    """
    mode_icons = {
        "AUTO": "mdi:auto-fix",
        "MANUAL": "mdi:hand-back-right",
        "DISABLED": "mdi:stop-circle"
    }

    return {
        "name": f"Pump Mode {mode.title()}",
        "unique_id": f"pump_mode_{mode.lower()}_{MQTT_CLIENT_ID}",
        "command_topic": f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/mode/set",
        "availability_topic": TOPIC_AVAILABILITY,
        "payload_press": mode,
        "icon": mode_icons.get(mode, "mdi:button-pointer"),
        "qos": 1,
        "device": {
            "identifiers": [f"hydrosense_{MQTT_CLIENT_ID}"],
            "name": f"HydroSense {MQTT_CLIENT_ID}",
            "model": "Raspberry Pi LED Controller",
            "manufacturer": "HydroSense"
        }
    }


# ============================================================================
# MQTTService Class
# ============================================================================

class MQTTService:
    """
    MQTT service for Home Assistant integration.

    Runs as FastAPI lifespan background task.
    Handles bidirectional communication with Home Assistant.
    """

    def __init__(self, execute_command_callback: Callable):
        """
        Initialize MQTT service.

        Args:
            execute_command_callback: Function to execute LED commands
                                     Signature: async def(command: dict) -> None
        """
        self.execute_command = execute_command_callback
        self.client: Optional[aiomqtt.Client] = None
        self.running = False
        self._last_published_state: Optional[dict] = None
        self._state_publish_lock = asyncio.Lock()

    async def start(self):
        """Start MQTT service (runs until cancelled)."""
        if not MQTT_ENABLED:
            logger.info("MQTT is disabled in configuration")
            return

        self.running = True
        logger.info(f"Starting MQTT service: broker={MQTT_BROKER}:{MQTT_PORT}, client_id={MQTT_CLIENT_ID}")

        # Retry connection with exponential backoff
        reconnect_interval = 5  # seconds

        while self.running:
            try:
                async with AsyncExitStack() as stack:
                    # Setup Last Will and Testament (LWT)
                    will = aiomqtt.Will(
                        topic=TOPIC_AVAILABILITY,
                        payload="offline",
                        qos=1,
                        retain=True,
                    )

                    # Connect to MQTT broker
                    self.client = aiomqtt.Client(
                        hostname=MQTT_BROKER,
                        port=MQTT_PORT,
                        username=MQTT_USERNAME,
                        password=MQTT_PASSWORD,
                        identifier=MQTT_CLIENT_ID,
                        will=will,
                    )

                    await stack.enter_async_context(self.client)
                    logger.info("Connected to MQTT broker")

                    # Publish availability (online)
                    await self.client.publish(
                        TOPIC_AVAILABILITY,
                        payload="online",
                        qos=1,
                        retain=True,
                    )

                    # Publish Home Assistant Discovery config
                    await self._publish_ha_discovery()

                    # Subscribe to command topics
                    await self.client.subscribe(TOPIC_HA_COMMAND, qos=1)
                    await self.client.subscribe(TOPIC_GRADIENT_COMMAND, qos=1)

                    # Subscribe to relay command topics
                    from app.config import RELAY_ENABLED
                    if RELAY_ENABLED:
                        from app.main import relay_manager
                        if relay_manager:
                            relay_ids = relay_manager.get_relay_ids()
                            for relay_id in relay_ids:
                                relay_command_topic = f"homeassistant/switch/{relay_id}/set"
                                await self.client.subscribe(relay_command_topic, qos=1)
                                logger.info(f"Subscribed to relay command topic: {relay_command_topic}")

                    # Subscribe to pump automation command topics
                    from app.config import PUMP_AUTOMATION_ENABLED
                    if PUMP_AUTOMATION_ENABLED:
                        from app.main import pump_automation
                        if pump_automation:
                            pump_mode_command_topic = f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/mode/set"
                            await self.client.subscribe(pump_mode_command_topic, qos=1)
                            logger.info(f"Subscribed to pump automation mode command topic: {pump_mode_command_topic}")

                    logger.info("Subscribed to all command topics")

                    # Publish initial state
                    await self.publish_state()

                    # Reset reconnect interval on successful connection
                    reconnect_interval = 5

                    # Listen for messages
                    async for message in self.client.messages:
                        await self._handle_message(message)

            except aiomqtt.MqttError as e:
                logger.error(f"MQTT connection error: {e}", exc_info=True)
                if self.running:
                    logger.info(f"Reconnecting in {reconnect_interval} seconds...")
                    await asyncio.sleep(reconnect_interval)
                    reconnect_interval = min(reconnect_interval * 2, 60)  # Max 60s

            except asyncio.CancelledError:
                logger.info("MQTT service cancelled")
                break

            except Exception as e:
                logger.error(f"Unexpected error in MQTT service: {e}", exc_info=True)
                if self.running:
                    await asyncio.sleep(reconnect_interval)

        # Cleanup
        if self.client:
            try:
                await self.client.publish(
                    TOPIC_AVAILABILITY,
                    payload="offline",
                    qos=1,
                    retain=True,
                )
            except Exception as e:
                logger.warning(f"Failed to publish offline status: {e}")

        logger.info("MQTT service stopped")

    async def stop(self):
        """Stop MQTT service."""
        logger.info("Stopping MQTT service...")
        self.running = False

    # ------------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------------

    async def _publish_ha_discovery(self):
        """Publish Home Assistant MQTT Discovery configuration."""
        try:
            # Publish LED light discovery
            config = get_ha_discovery_config()
            await self.client.publish(
                TOPIC_HA_CONFIG,
                payload=json.dumps(config),
                qos=1,
                retain=True,
            )
            logger.info("Published Home Assistant discovery config for LED")

            # Publish temperature sensor discovery
            from app.config import TEMP_ENABLED
            if TEMP_ENABLED:
                # Import here to avoid circular dependency
                from app.main import temp_manager
                if temp_manager:
                    sensor_ids = temp_manager.get_sensor_ids()
                    for sensor_id in sensor_ids:
                        topic = f"homeassistant/sensor/{MQTT_CLIENT_ID}_{sensor_id}/config"
                        temp_config = get_temp_sensor_discovery_config(sensor_id)

                        await self.client.publish(
                            topic,
                            payload=json.dumps(temp_config),
                            qos=1,
                            retain=True,
                        )
                        logger.info(f"Published HA discovery config for temperature sensor {sensor_id}")

            # Publish relay switch discovery
            from app.config import RELAY_ENABLED
            if RELAY_ENABLED:
                # Import here to avoid circular dependency
                from app.main import relay_manager
                if relay_manager:
                    relay_ids = relay_manager.get_relay_ids()
                    for relay_id in relay_ids:
                        relay_info = relay_manager.get_relay_info(relay_id)
                        topic = f"homeassistant/switch/{relay_id}/config"
                        relay_config = get_relay_discovery_config(relay_id, relay_info['name'])

                        await self.client.publish(
                            topic,
                            payload=json.dumps(relay_config),
                            qos=1,
                            retain=True,
                        )
                        logger.info(f"Published HA discovery config for relay switch {relay_id}")

                        # Publish initial state
                        state_topic = f"homeassistant/switch/{relay_id}/state"
                        from app.relay import RelayState
                        state_payload = "ON" if relay_info['state'] == RelayState.ON else "OFF"
                        await self.client.publish(
                            state_topic,
                            payload=state_payload,
                            qos=1,
                            retain=True,
                        )

            # Publish water level sensor discovery
            from app.config import WATER_LEVEL_ENABLED
            if WATER_LEVEL_ENABLED:
                # Import here to avoid circular dependency
                from app.main import water_sensor
                if water_sensor:
                    topic = f"homeassistant/binary_sensor/water_level_{MQTT_CLIENT_ID}/config"
                    water_config = get_water_level_discovery_config()

                    await self.client.publish(
                        topic,
                        payload=json.dumps(water_config),
                        qos=1,
                        retain=True,
                    )
                    logger.info(f"Published HA discovery config for water level sensor")

                    # Publish initial state
                    water_info = water_sensor.get_info()
                    await self.publish_water_level_state(water_info)

            # Publish pump automation discovery
            from app.config import PUMP_AUTOMATION_ENABLED
            if PUMP_AUTOMATION_ENABLED:
                # Import here to avoid circular dependency
                from app.main import pump_automation
                if pump_automation:
                    # Publish pump mode sensor
                    mode_topic = f"homeassistant/sensor/pump_mode_{MQTT_CLIENT_ID}/config"
                    mode_config = get_pump_mode_sensor_discovery_config()
                    await self.client.publish(
                        mode_topic,
                        payload=json.dumps(mode_config),
                        qos=1,
                        retain=True,
                    )
                    logger.info(f"Published HA discovery config for pump mode sensor")

                    # Publish pump runtime sensor
                    runtime_topic = f"homeassistant/sensor/pump_runtime_{MQTT_CLIENT_ID}/config"
                    runtime_config = get_pump_runtime_sensor_discovery_config()
                    await self.client.publish(
                        runtime_topic,
                        payload=json.dumps(runtime_config),
                        qos=1,
                        retain=True,
                    )
                    logger.info(f"Published HA discovery config for pump runtime sensor")

                    # Publish pump mode buttons (AUTO, MANUAL, DISABLED)
                    for mode in ["AUTO", "MANUAL", "DISABLED"]:
                        button_topic = f"homeassistant/button/pump_mode_{mode.lower()}_{MQTT_CLIENT_ID}/config"
                        button_config = get_pump_mode_button_discovery_config(mode)
                        await self.client.publish(
                            button_topic,
                            payload=json.dumps(button_config),
                            qos=1,
                            retain=True,
                        )
                        logger.info(f"Published HA discovery config for pump mode button: {mode}")

                    # Publish initial state
                    pump_status = pump_automation.get_status()
                    await self.publish_pump_automation_state(pump_status)

        except Exception as e:
            logger.error(f"Failed to publish HA discovery config: {e}", exc_info=True)

    # ------------------------------------------------------------------------
    # Message Handling
    # ------------------------------------------------------------------------

    async def _handle_message(self, message: aiomqtt.Message):
        """
        Handle incoming MQTT message.

        Args:
            message: aiomqtt.Message instance
        """
        try:
            topic = str(message.topic)
            payload = message.payload.decode()

            logger.debug(f"MQTT message received: topic={topic}, payload={payload}")

            if topic == TOPIC_HA_COMMAND:
                await self._handle_ha_command(payload)
            elif topic == TOPIC_GRADIENT_COMMAND:
                await self._handle_gradient_command(payload)
            elif topic.startswith("homeassistant/switch/") and topic.endswith("/set"):
                # Extract relay_id from topic: homeassistant/switch/{relay_id}/set
                relay_id = topic.split("/")[2]
                await self._handle_relay_command(relay_id, payload)
            elif topic == f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/mode/set":
                await self._handle_pump_mode_command(payload)
            else:
                logger.warning(f"Unknown MQTT topic: {topic}")

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}", exc_info=True)

    async def _handle_ha_command(self, payload: str):
        """
        Handle Home Assistant light command.

        Payload format (JSON):
        {
            "state": "ON" | "OFF",
            "brightness": 0-255,
            "color": {"r": 0-255, "g": 0-255, "b": 0-255},
            "effect": "none" | "gradient_shift" | "gradient_pulse" | "rainbow"
        }

        Args:
            payload: JSON string from HA
        """
        try:
            command = json.loads(payload)
            logger.info(f"HA command received: {command}")

            # Execute command (calls REST API logic)
            await self.execute_command(command)

            # Publish updated state back to HA
            await self.publish_state()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in HA command: {e}")
        except Exception as e:
            logger.error(f"Error executing HA command: {e}", exc_info=True)

    async def _handle_gradient_command(self, payload: str):
        """
        Handle gradient-specific command.

        Payload format (JSON):
        {
            "action": "load_preset" | "save_preset" | "static" | "animated",
            "preset_name": "sunset",  # for load_preset
            "config": {...}  # GradientConfig dict
        }

        Args:
            payload: JSON string
        """
        try:
            command = json.loads(payload)
            logger.info(f"Gradient command received: {command}")

            # Execute gradient command
            await self.execute_command({"type": "gradient", **command})

            # Publish updated state
            await self.publish_state()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in gradient command: {e}")
        except Exception as e:
            logger.error(f"Error executing gradient command: {e}", exc_info=True)

    async def _handle_relay_command(self, relay_id: str, payload: str):
        """
        Handle relay switch command from Home Assistant.

        Payload format: "ON" or "OFF"

        Args:
            relay_id: Relay identifier
            payload: Command string ("ON" or "OFF")
        """
        try:
            logger.info(f"Relay command received for '{relay_id}': {payload}")

            from app.config import RELAY_ENABLED
            if not RELAY_ENABLED:
                logger.warning("Relay command received but RELAY_ENABLED=false")
                return

            from app.main import relay_manager
            if not relay_manager:
                logger.warning("Relay command received but relay_manager not initialized")
                return

            from app.relay import RelayState
            import asyncio

            # Execute relay command
            if payload == "ON":
                await asyncio.to_thread(relay_manager.turn_on, relay_id)
            elif payload == "OFF":
                await asyncio.to_thread(relay_manager.turn_off, relay_id)
            else:
                logger.warning(f"Unknown relay command: {payload}")
                return

            # Publish updated state back to MQTT
            new_state = relay_manager.get_state(relay_id)
            state_topic = f"homeassistant/switch/{relay_id}/state"
            state_payload = "ON" if new_state == RelayState.ON else "OFF"

            await self.client.publish(
                state_topic,
                payload=state_payload,
                qos=1,
                retain=True,
            )
            logger.info(f"Published relay state for '{relay_id}': {state_payload}")

        except KeyError:
            logger.error(f"Relay '{relay_id}' not found")
        except Exception as e:
            logger.error(f"Error executing relay command for '{relay_id}': {e}", exc_info=True)

    async def _handle_pump_mode_command(self, payload: str):
        """
        Handle pump automation mode change command from Home Assistant.

        Payload format: "AUTO" or "MANUAL" or "DISABLED"

        Args:
            payload: Command string (mode name)
        """
        try:
            logger.info(f"Pump mode command received: {payload}")

            from app.config import PUMP_AUTOMATION_ENABLED
            if not PUMP_AUTOMATION_ENABLED:
                logger.warning("Pump mode command received but PUMP_AUTOMATION_ENABLED=false")
                return

            from app.main import pump_automation
            if not pump_automation:
                logger.warning("Pump mode command received but pump_automation not initialized")
                return

            from app.pump_automation import AutomationMode
            import asyncio

            # Validate and execute mode change
            try:
                mode = AutomationMode(payload)
                await asyncio.to_thread(pump_automation.set_mode, mode)
                logger.info(f"Pump automation mode set to: {mode}")

                # Publish updated state back to MQTT
                pump_status = pump_automation.get_status()
                await self.publish_pump_automation_state(pump_status)

            except ValueError:
                logger.error(f"Invalid pump mode: {payload}. Valid modes: AUTO, MANUAL, DISABLED")

        except Exception as e:
            logger.error(f"Error executing pump mode command: {e}", exc_info=True)

    # ------------------------------------------------------------------------
    # State Publishing
    # ------------------------------------------------------------------------

    async def publish_state(self, force: bool = False):
        """
        Publish current LED state to MQTT.

        Args:
            force: Publish even if state hasn't changed

        State is published to:
        - homeassistant/light/led_strip/state (for HA light entity)
        - hydrosense/gradient/state (for gradient configuration)
        """
        if not self.client:
            return

        async with self._state_publish_lock:
            try:
                # Get current state
                state_payload = led_state.to_mqtt_payload()

                # Skip if state hasn't changed (debounce)
                if not force and state_payload == self._last_published_state:
                    logger.debug("State unchanged, skipping publish")
                    return

                # Publish to HA state topic
                await self.client.publish(
                    TOPIC_HA_STATE,
                    payload=json.dumps(state_payload),
                    qos=1,
                    retain=True,
                )

                # Publish gradient state if in gradient mode
                if led_state.mode in ["gradient_static", "gradient_animated"]:
                    gradient_payload = {
                        "mode": led_state.mode,
                        "config": led_state.gradient_config,
                        "animation": led_state.active_animation,
                    }
                    await self.client.publish(
                        TOPIC_GRADIENT_STATE,
                        payload=json.dumps(gradient_payload),
                        qos=1,
                        retain=True,
                    )

                self._last_published_state = state_payload
                logger.debug(f"Published state to MQTT: {state_payload}")

            except Exception as e:
                logger.error(f"Failed to publish state: {e}", exc_info=True)

    async def publish_temperature_state(self, sensor_id: str, reading: dict):
        """
        Publish temperature reading to MQTT.

        Args:
            sensor_id: Sensor ID
            reading: Temperature reading dict
        """
        if not self.client:
            return

        try:
            topic = f"hydrosense/{MQTT_CLIENT_ID}/temperature/{sensor_id}/state"

            # Format payload for HA
            temp_value = reading["celsius"] if TEMP_UNIT == "celsius" else reading["fahrenheit"]
            payload = {
                "temperature": temp_value,
                "sensor_id": sensor_id,
                "valid": reading["valid"],
                "timestamp": reading["timestamp"]
            }

            if reading.get("error"):
                payload["error"] = reading["error"]

            await self.client.publish(
                topic,
                payload=json.dumps(payload),
                qos=1,
                retain=True,
            )

            logger.debug(f"Published temperature for {sensor_id}: {temp_value}°")

        except Exception as e:
            logger.error(f"Failed to publish temperature for {sensor_id}: {e}", exc_info=True)

    async def publish_water_level_state(self, water_level_info: dict):
        """
        Publish water level sensor state to MQTT.

        Args:
            water_level_info: Water level sensor info dict from get_info()
        """
        if not self.client:
            return

        try:
            topic = f"hydrosense/{MQTT_CLIENT_ID}/water_level/state"

            # Format payload for HA
            payload = {
                "current_level": water_level_info["current_level"],
                "gpio_pin": water_level_info["gpio_pin"],
                "gpio_state": water_level_info["gpio_state"],
                "last_change": water_level_info["last_change"],
                "active_high": water_level_info["active_high"]
            }

            await self.client.publish(
                topic,
                payload=json.dumps(payload),
                qos=1,
                retain=True,
            )

            logger.debug(f"Published water level state: {water_level_info['current_level']}")

        except Exception as e:
            logger.error(f"Failed to publish water level state: {e}", exc_info=True)

    async def publish_pump_automation_state(self, pump_status: dict):
        """
        Publish pump automation state to MQTT.

        Args:
            pump_status: Pump automation status dict from get_status()
        """
        if not self.client:
            return

        try:
            topic = f"hydrosense/{MQTT_CLIENT_ID}/pump_automation/state"

            # Format payload for HA (convert enum to string)
            from app.relay import RelayState
            payload = {
                "mode": pump_status["mode"],
                "water_level": pump_status["water_level"],
                "pump_state": pump_status["pump_state"].value if isinstance(pump_status["pump_state"], RelayState) else pump_status["pump_state"],
                "pump_relay_id": pump_status["pump_relay_id"],
                "on_interval": pump_status["on_interval"],
                "off_interval": pump_status["off_interval"],
                "max_runtime": pump_status["max_runtime"],
                "cycle_count": pump_status["cycle_count"],
                "total_runtime": pump_status["total_runtime"],
                "automation_active": pump_status["automation_active"],
                "next_action": pump_status.get("next_action"),
                "next_action_in": pump_status.get("next_action_in")
            }

            # Add optional fields if present
            if "running_since" in pump_status:
                payload["running_since"] = pump_status["running_since"]
                payload["current_runtime"] = pump_status["current_runtime"]
                payload["runtime_remaining"] = pump_status["runtime_remaining"]

            await self.client.publish(
                topic,
                payload=json.dumps(payload),
                qos=1,
                retain=True,
            )

            logger.debug(f"Published pump automation state: mode={pump_status['mode']}, pump={payload['pump_state']}")

        except Exception as e:
            logger.error(f"Failed to publish pump automation state: {e}", exc_info=True)


# ============================================================================
# Global Instance (initialized in main.py)
# ============================================================================

mqtt_service: Optional[MQTTService] = None


def init_mqtt_service(execute_command_callback: Callable) -> MQTTService:
    """
    Initialize global MQTT service instance.

    Args:
        execute_command_callback: Function to execute LED commands

    Returns:
        MQTTService instance
    """
    global mqtt_service
    mqtt_service = MQTTService(execute_command_callback)
    return mqtt_service


async def publish_state_to_mqtt(force: bool = False):
    """
    Publish current LED state to MQTT (convenience function).

    Args:
        force: Publish even if state hasn't changed
    """
    if mqtt_service:
        await mqtt_service.publish_state(force=force)


async def publish_water_level_to_mqtt(water_level_info: dict):
    """
    Publish water level sensor state to MQTT (convenience function).

    Args:
        water_level_info: Water level sensor info dict from get_info()
    """
    if mqtt_service:
        await mqtt_service.publish_water_level_state(water_level_info)


async def publish_pump_automation_to_mqtt(pump_status: dict):
    """
    Publish pump automation state to MQTT (convenience function).

    Args:
        pump_status: Pump automation status dict from get_status()
    """
    if mqtt_service:
        await mqtt_service.publish_pump_automation_state(pump_status)
