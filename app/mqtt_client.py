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
                    logger.info("Subscribed to command topics")

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
