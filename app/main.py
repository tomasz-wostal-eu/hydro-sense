"""
HTTP API for human-centric lighting.

IMPORTANT:
- Must run with ONE worker
- Must run under sudo (-E) because of DMA access
"""

from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel, Field
from typing import Literal
from contextlib import asynccontextmanager
import threading
import signal
import sys
import asyncio
from datetime import datetime

from app.led import LedStrip
from app.animations import cloudy_sunrise, cloudy_sunset
from app.solar_time import get_sun_times
from app.season_profiles import SEASONS
from app.config import LED_COUNT, LED_PIN, LOG_LEVEL
from app.logger import logger
from app.state import led_state
from app.gradient import (
    ColorStop,
    GradientConfig,
    render_gradient,
    animate_gradient,
    validate_gradient_config
)
from app.gradient_presets import (
    GradientPreset,
    load_presets,
    save_preset,
    get_preset,
    delete_preset,
    list_preset_names
)
from app.mqtt_client import init_mqtt_service, publish_state_to_mqtt
from app.config import MQTT_ENABLED, TEMP_ENABLED, TEMP_SENSOR_IDS, TEMP_UNIT, TEMP_UPDATE_INTERVAL
from app.temperature import TemperatureSensorManager, TemperatureReading
from typing import Optional


# ============================================================================
# Hardware and state initialization
# ============================================================================

leds = LedStrip(count=LED_COUNT)

# Thread management
active_threads: dict[str, tuple[threading.Thread, threading.Event]] = {}
shutdown_event = threading.Event()

# Temperature sensor manager
temp_manager: Optional[TemperatureSensorManager] = None
if TEMP_ENABLED:
    try:
        sensor_ids = [s.strip() for s in TEMP_SENSOR_IDS.split(',') if s.strip()] if TEMP_SENSOR_IDS else []
        temp_manager = TemperatureSensorManager(sensor_ids=sensor_ids if sensor_ids else None)
        logger.info(f"Temperature sensor manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize temperature sensors: {e}", exc_info=True)
        temp_manager = None


# ============================================================================
# MQTT Command Bridge
# ============================================================================

async def execute_command_bridge(command: dict):
    """
    Bridge MQTT commands to LED control functions.

    Handles commands from Home Assistant via MQTT.

    Args:
        command: Command dictionary from MQTT
            - For HA light commands: {"state": "ON", "brightness": 255, "color": {...}, "effect": "..."}
            - For gradient commands: {"type": "gradient", "action": "...", ...}
    """
    try:
        # HA Light command
        if "state" in command:
            state = command.get("state")

            if state == "OFF":
                # Turn off LEDs
                logger.info("MQTT command: Turn off")
                await asyncio.to_thread(_off_sync)
                led_state.update(mode="off", rgb=(0, 0, 0), brightness=0.0)

            elif state == "ON":
                # Get parameters
                brightness = command.get("brightness", 255) / 255.0  # HA uses 0-255
                color = command.get("color", {})
                effect = command.get("effect", "none")

                # Handle effects first
                if effect and effect != "none":
                    logger.info(f"MQTT command: Effect {effect}")

                    if effect == "gradient_shift":
                        # Load rainbow preset with shift animation
                        preset = get_preset("rainbow")
                        if preset:
                            preset.config.animation = "shift"
                            preset.config.brightness = brightness
                            await asyncio.to_thread(
                                run_async,
                                "gradient_shift",
                                animate_gradient,
                                leds,
                                preset.config,
                                0
                            )
                            led_state.update(
                                mode="gradient_animated",
                                gradient_config=preset.config.dict(),
                                active_animation="gradient_shift",
                                brightness=brightness
                            )

                    elif effect == "gradient_pulse":
                        # Load aurora preset (has pulse animation)
                        preset = get_preset("aurora")
                        if preset:
                            preset.config.brightness = brightness
                            await asyncio.to_thread(
                                run_async,
                                "gradient_pulse",
                                animate_gradient,
                                leds,
                                preset.config,
                                0
                            )
                            led_state.update(
                                mode="gradient_animated",
                                gradient_config=preset.config.dict(),
                                active_animation="gradient_pulse",
                                brightness=brightness
                            )

                    elif effect == "rainbow":
                        # Load rainbow preset
                        preset = get_preset("rainbow")
                        if preset:
                            preset.config.brightness = brightness
                            await asyncio.to_thread(
                                run_async,
                                "gradient_rainbow",
                                animate_gradient,
                                leds,
                                preset.config,
                                0
                            )
                            led_state.update(
                                mode="gradient_animated",
                                gradient_config=preset.config.dict(),
                                active_animation="gradient_rainbow",
                                brightness=brightness
                            )

                # Handle RGB color
                elif color and "r" in color:
                    r = color.get("r", 0)
                    g = color.get("g", 0)
                    b = color.get("b", 0)

                    logger.info(f"MQTT command: RGB ({r}, {g}, {b}), brightness={brightness}")
                    await asyncio.to_thread(leds.set_brightness, brightness)
                    await asyncio.to_thread(leds.set_rgb, r, g, b)

                    led_state.update(
                        mode="rgb",
                        rgb=(r, g, b),
                        brightness=brightness
                    )

                # Just brightness change (no color or effect)
                else:
                    logger.info(f"MQTT command: Brightness {brightness}")
                    await asyncio.to_thread(leds.set_brightness, brightness)

                    # Re-apply current color with new brightness
                    # (brightness is global multiplier, need to refresh LEDs)
                    current_rgb = led_state.rgb
                    await asyncio.to_thread(leds.set_rgb, current_rgb[0], current_rgb[1], current_rgb[2])

                    led_state.update(brightness=brightness)

        # Gradient-specific command
        elif command.get("type") == "gradient":
            action = command.get("action")

            if action == "load_preset":
                preset_name = command.get("preset_name")
                logger.info(f"MQTT command: Load gradient preset {preset_name}")

                preset = get_preset(preset_name)
                if preset:
                    if preset.config.animation:
                        await asyncio.to_thread(
                            run_async,
                            f"gradient_{preset.config.animation}",
                            animate_gradient,
                            leds,
                            preset.config,
                            0
                        )
                        led_state.update(
                            mode="gradient_animated",
                            gradient_config=preset.config.dict(),
                            active_animation=f"gradient_{preset.config.animation}",
                            brightness=preset.config.brightness
                        )
                    else:
                        colors = await asyncio.to_thread(render_gradient, preset.config.stops, LED_COUNT)
                        await asyncio.to_thread(leds.set_brightness, preset.config.brightness)
                        await asyncio.to_thread(leds.set_pixel_array, colors)
                        led_state.update(
                            mode="gradient_static",
                            gradient_config=preset.config.dict(),
                            brightness=preset.config.brightness,
                            rgb=colors[0] if colors else (0, 0, 0)
                        )

            elif action == "static":
                # Apply static gradient from MQTT
                config_data = command.get("config", {})
                logger.info(f"MQTT command: Static gradient with {len(config_data.get('stops', []))} stops")

                try:
                    config = GradientConfig(**config_data)
                    validate_gradient_config(config)

                    colors = await asyncio.to_thread(render_gradient, config.stops, LED_COUNT)
                    await asyncio.to_thread(leds.set_brightness, config.brightness)
                    await asyncio.to_thread(leds.set_pixel_array, colors)

                    led_state.update(
                        mode="gradient_static",
                        gradient_config=config.dict(),
                        brightness=config.brightness,
                        rgb=colors[0] if colors else (0, 0, 0)
                    )
                except Exception as e:
                    logger.error(f"Failed to apply static gradient: {e}")

            elif action == "animated":
                # Start animated gradient from MQTT
                config_data = command.get("config", {})
                duration = command.get("duration", 0)
                logger.info(f"MQTT command: Animated gradient ({config_data.get('animation')}), duration={duration}s")

                try:
                    config = GradientConfig(**config_data)
                    validate_gradient_config(config)

                    animation_name = f"gradient_{config.animation}"
                    await asyncio.to_thread(
                        run_async,
                        animation_name,
                        animate_gradient,
                        leds,
                        config,
                        duration
                    )

                    led_state.update(
                        mode="gradient_animated",
                        gradient_config=config.dict(),
                        active_animation=animation_name,
                        brightness=config.brightness
                    )
                except Exception as e:
                    logger.error(f"Failed to start animated gradient: {e}")

            elif action == "save_preset":
                # Save custom gradient as preset from MQTT
                preset_name = command.get("preset_name")
                config_data = command.get("config", {})
                description = command.get("description", "")
                logger.info(f"MQTT command: Save gradient preset '{preset_name}'")

                try:
                    config = GradientConfig(**config_data)
                    validate_gradient_config(config)

                    preset = GradientPreset(
                        name=preset_name,
                        description=description,
                        config=config
                    )
                    await asyncio.to_thread(save_preset, preset)
                    logger.info(f"Saved gradient preset '{preset_name}' via MQTT")

                except Exception as e:
                    logger.error(f"Failed to save gradient preset: {e}")

            else:
                logger.warning(f"Unknown gradient action: {action}")

        else:
            logger.warning(f"Unknown MQTT command format: {command}")

    except Exception as e:
        logger.error(f"Failed to execute MQTT command: {e}", exc_info=True)


def _off_sync():
    """Synchronous helper for turning off LEDs (for asyncio.to_thread)."""
    # Cancel all animations
    for name, (thread, cancel_event) in list(active_threads.items()):
        logger.info(f"Cancelling animation: {name}")
        cancel_event.set()

    # Wait briefly for animations to stop
    for name, (thread, cancel_event) in list(active_threads.items()):
        thread.join(timeout=2.0)
        if thread.is_alive():
            logger.warning(f"Animation {name} did not stop within timeout")

    # Turn off LEDs
    leds.off()


# ============================================================================
# FastAPI Lifespan (MQTT background task)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Starts MQTT service as background task on startup.
    Stops MQTT service on shutdown.
    """
    logger.info("HydroSense starting up")
    logger.info(f"Configuration: LED_COUNT={LED_COUNT}, LED_PIN={LED_PIN}, LOG_LEVEL={LOG_LEVEL}")
    logger.info(f"MQTT enabled: {MQTT_ENABLED}")

    # Start MQTT service if enabled
    mqtt_task = None
    if MQTT_ENABLED:
        mqtt_service = init_mqtt_service(execute_command_bridge)
        mqtt_task = asyncio.create_task(mqtt_service.start())
        logger.info("MQTT service started as background task")

    # Start temperature polling if enabled
    temp_task = None
    if TEMP_ENABLED and temp_manager:
        async def poll_temperature():
            """Background task to poll temperature sensors."""
            while True:
                try:
                    readings = await asyncio.to_thread(temp_manager.read_all)
                    sensors_data = {
                        sensor_id: {
                            "celsius": reading.celsius,
                            "fahrenheit": reading.fahrenheit,
                            "timestamp": reading.timestamp,
                            "valid": reading.valid,
                            "error": reading.error
                        }
                        for sensor_id, reading in readings.items()
                    }

                    led_state.update(
                        temperature_readings=sensors_data,
                        last_temp_update=datetime.now()
                    )

                    # Publish to MQTT
                    if mqtt_service:
                        for sensor_id, reading_dict in sensors_data.items():
                            await mqtt_service.publish_temperature_state(sensor_id, reading_dict)

                except Exception as e:
                    logger.error("Temperature polling error", exc_info=True)

                await asyncio.sleep(TEMP_UPDATE_INTERVAL)

        temp_task = asyncio.create_task(poll_temperature())
        logger.info(f"Temperature polling started (interval: {TEMP_UPDATE_INTERVAL}s)")

    # App is running
    yield

    # Shutdown sequence
    logger.info("Starting graceful shutdown...")

    # 1. Cancel all running animations
    for name, (thread, cancel_event) in list(active_threads.items()):
        logger.info(f"Cancelling animation: {name}")
        cancel_event.set()

    # 2. Wait briefly for animations to stop
    for name, (thread, cancel_event) in list(active_threads.items()):
        thread.join(timeout=2.0)
        if thread.is_alive():
            logger.warning(f"Animation {name} did not stop within timeout")

    # 3. Stop temperature polling
    if temp_task:
        logger.info("Stopping temperature polling...")
        temp_task.cancel()
        try:
            await temp_task
        except asyncio.CancelledError:
            logger.info("Temperature polling stopped")

    # 4. Stop MQTT
    if mqtt_task:
        logger.info("Stopping MQTT service...")
        mqtt_task.cancel()
        try:
            await mqtt_task
        except asyncio.CancelledError:
            logger.info("MQTT service stopped")

    # 5. Turn off LEDs
    try:
        logger.info("Turning off LEDs")
        leds.off()
    except Exception as e:
        logger.error("Failed to turn off LEDs during shutdown", exc_info=True)

    logger.info("Shutdown complete")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="HydroSense API",
    lifespan=lifespan
)

# Backlight control router (all LED/gradient endpoints)
backlight_router = APIRouter(
    prefix="/backlight",
    tags=["Backlight Control"]
)


# ------------------------------------------------------------------

class RGBRequest(BaseModel):
    r: int = Field(..., ge=0, le=255, description="Red component (0-255)")
    g: int = Field(..., ge=0, le=255, description="Green component (0-255)")
    b: int = Field(..., ge=0, le=255, description="Blue component (0-255)")
    brightness: float = Field(1.0, ge=0.0, le=1.0, description="Brightness level (0.0-1.0)")


class HSVRequest(BaseModel):
    h: float = Field(..., description="Hue in degrees (0-360)")
    s: float = Field(1.0, ge=0.0, le=1.0, description="Saturation (0.0-1.0)")
    v: float = Field(1.0, ge=0.0, le=1.0, description="Value/brightness (0.0-1.0)")
    brightness: float = Field(1.0, ge=0.0, le=1.0, description="Global brightness (0.0-1.0)")


class SolarRequest(BaseModel):
    latitude: float = Field(53.1235, ge=-90, le=90, description="Latitude (-90 to 90), default: Bydgoszcz, Poland")
    longitude: float = Field(18.0084, ge=-180, le=180, description="Longitude (-180 to 180), default: Bydgoszcz, Poland")
    season: str = Field("spring", description="Season: winter, spring, summer, autumn")
    duration_override: int | None = Field(None, description="Override duration in seconds")


class GradientStaticRequest(BaseModel):
    stops: list[ColorStop] = Field(..., min_items=2, description="Color stops (at least 2 required)")
    brightness: float = Field(1.0, ge=0.0, le=1.0, description="Global brightness (0.0-1.0)")


class GradientAnimatedRequest(BaseModel):
    stops: list[ColorStop] = Field(..., min_items=2, description="Color stops (at least 2 required)")
    brightness: float = Field(1.0, ge=0.0, le=1.0, description="Global brightness (0.0-1.0)")
    animation: Literal["shift", "pulse", "rainbow"] = Field(..., description="Animation type")
    speed: float = Field(1.0, gt=0.0, description="Animation speed multiplier")
    direction: Literal["forward", "backward"] = Field("forward", description="Animation direction")
    duration: int = Field(0, ge=0, description="Duration in seconds (0 = infinite)")


def run_async(name: str, fn, *args):
    """Run animation in managed background thread with cancellation support."""

    # Cancel existing animation with same name
    if name in active_threads:
        logger.info(f"Cancelling existing animation: {name}")
        thread, cancel_event = active_threads[name]
        cancel_event.set()
        thread.join(timeout=2.0)

    cancel_event = threading.Event()

    def wrapper():
        try:
            logger.info(f"Starting animation thread: {name}")
            fn(*args, cancel_event)
            logger.info(f"Animation thread completed: {name}")
        except Exception as e:
            logger.error(f"Animation thread failed: {name}", exc_info=True)
        finally:
            active_threads.pop(name, None)

    thread = threading.Thread(target=wrapper, name=name, daemon=False)
    active_threads[name] = (thread, cancel_event)
    thread.start()


def shutdown_handler(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    shutdown_event.set()

    # Cancel all running animations
    for name, (thread, cancel_event) in list(active_threads.items()):
        logger.info(f"Cancelling animation: {name}")
        cancel_event.set()

    # Wait for threads to finish (with timeout)
    for name, (thread, cancel_event) in list(active_threads.items()):
        thread.join(timeout=5.0)
        if thread.is_alive():
            logger.warning(f"Thread {name} did not stop within timeout")

    # Turn off LEDs
    try:
        logger.info("Turning off LEDs")
        leds.off()
    except Exception as e:
        logger.error("Failed to turn off LEDs during shutdown", exc_info=True)

    logger.info("Shutdown complete")
    # Note: Don't call sys.exit() here - let uvicorn handle shutdown gracefully


# Register signal handlers
signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
logger.info("Registered signal handlers for graceful shutdown")


# ------------------------------------------------------------------
# Basic control
# ------------------------------------------------------------------

@backlight_router.post("/rgb")
async def set_rgb(req: RGBRequest):
    try:
        logger.debug(f"RGB request: r={req.r}, g={req.g}, b={req.b}, brightness={req.brightness}")
        leds.set_brightness(req.brightness)
        leds.set_rgb(req.r, req.g, req.b)

        # Update state
        led_state.update(
            mode="rgb",
            rgb=(req.r, req.g, req.b),
            brightness=req.brightness
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to set RGB", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.post("/hsv")
async def set_hsv(req: HSVRequest):
    try:
        logger.debug(f"HSV request: h={req.h}, s={req.s}, v={req.v}, brightness={req.brightness}")
        leds.set_brightness(req.brightness)
        leds.set_hsv(req.h, req.s, req.v)

        # Convert HSV to RGB for state
        import colorsys
        h_normalized = (req.h % 360) / 360.0
        s_normalized = max(0.0, min(1.0, req.s))
        v_normalized = max(0.0, min(1.0, req.v))
        r, g, b = colorsys.hsv_to_rgb(h_normalized, s_normalized, v_normalized)

        # Update state
        led_state.update(
            mode="hsv",
            rgb=(int(r * 255), int(g * 255), int(b * 255)),
            brightness=req.brightness
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to set HSV", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.post("/off")
async def off():
    try:
        # Cancel all running animations first
        cancelled_animations = []
        for name, (thread, cancel_event) in list(active_threads.items()):
            logger.info(f"Cancelling animation: {name}")
            cancel_event.set()
            cancelled_animations.append(name)

        # Wait briefly for animations to stop (max 2 seconds)
        for name, (thread, cancel_event) in list(active_threads.items()):
            thread.join(timeout=2.0)
            if thread.is_alive():
                logger.warning(f"Animation {name} did not stop within timeout")

        # Now turn off LEDs
        logger.info("Turning off LEDs")
        leds.off()

        # Update state
        led_state.update(
            mode="off",
            rgb=(0, 0, 0),
            brightness=0.0,
            gradient_config=None,
            active_animation=None
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        return {
            "status": "off",
            "cancelled_animations": cancelled_animations
        }
    except Exception as e:
        logger.error("Failed to turn off LEDs", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Natural light modes
# ------------------------------------------------------------------

@backlight_router.post("/sunrise/auto")
async def sunrise_auto(req: SolarRequest):
    try:
        # Validate season
        if req.season not in SEASONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid season: {req.season}. Must be one of: {', '.join(SEASONS.keys())}"
            )

        sunrise, _ = get_sun_times(req.latitude, req.longitude)
        now = datetime.now(sunrise.tzinfo)

        duration = int((sunrise - now).total_seconds())
        if req.duration_override:
            duration = req.duration_override
        duration = max(300, duration)

        logger.info(f"Starting sunrise animation: duration={duration}s, season={req.season}, lat={req.latitude}, lon={req.longitude}")
        run_async("sunrise", cloudy_sunrise, leds, duration, req.season)

        # Update state
        led_state.update(
            mode="sunrise",
            active_animation="sunrise"
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        return {"mode": "cloudy_sunrise", "duration": duration}

    except HTTPException:
        raise
    except ValueError as e:
        # Astral library error for extreme locations (polar regions, etc.)
        error_msg = str(e)
        if "never reaches" in error_msg.lower() or "domain error" in error_msg.lower():
            logger.warning(f"Cannot calculate sunrise for location: lat={req.latitude}, lon={req.longitude}, error={error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot calculate sunrise/sunset times for this location (lat={req.latitude}, lon={req.longitude}). "
                       f"This may occur in polar regions or during certain seasons. "
                       f"Try using duration_override parameter to set a fixed duration instead."
            )
        else:
            logger.error("Failed to start sunrise animation", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Failed to start sunrise animation", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.post("/sunset/auto")
async def sunset_auto(req: SolarRequest):
    try:
        # Validate season
        if req.season not in SEASONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid season: {req.season}. Must be one of: {', '.join(SEASONS.keys())}"
            )

        _, sunset = get_sun_times(req.latitude, req.longitude)
        now = datetime.now(sunset.tzinfo)

        duration = int((sunset - now).total_seconds())
        if req.duration_override:
            duration = req.duration_override
        duration = max(300, duration)

        logger.info(f"Starting sunset animation: duration={duration}s, season={req.season}, lat={req.latitude}, lon={req.longitude}")
        run_async("sunset", cloudy_sunset, leds, duration, req.season)

        # Update state
        led_state.update(
            mode="sunset",
            active_animation="sunset"
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        return {"mode": "cloudy_sunset", "duration": duration}

    except HTTPException:
        raise
    except ValueError as e:
        # Astral library error for extreme locations (polar regions, etc.)
        error_msg = str(e)
        if "never reaches" in error_msg.lower() or "domain error" in error_msg.lower():
            logger.warning(f"Cannot calculate sunset for location: lat={req.latitude}, lon={req.longitude}, error={error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot calculate sunrise/sunset times for this location (lat={req.latitude}, lon={req.longitude}). "
                       f"This may occur in polar regions or during certain seasons. "
                       f"Try using duration_override parameter to set a fixed duration instead."
            )
        else:
            logger.error("Failed to start sunset animation", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Failed to start sunset animation", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Gradient control
# ------------------------------------------------------------------

@backlight_router.post("/gradient/static")
async def set_gradient_static(req: GradientStaticRequest):
    """
    Set static gradient (no animation).

    Example:
        {
          "stops": [
            {"position": 0.0, "r": 255, "g": 0, "b": 0},
            {"position": 1.0, "r": 0, "g": 0, "b": 255}
          ],
          "brightness": 0.8
        }
    """
    try:
        # Create config and validate
        config = GradientConfig(
            stops=req.stops,
            brightness=req.brightness,
            animation=None,
            speed=1.0,
            direction="forward"
        )
        validate_gradient_config(config)

        # Render gradient to pixel array
        colors = render_gradient(config.stops, LED_COUNT)

        # Apply to LEDs
        leds.set_brightness(config.brightness)
        leds.set_pixel_array(colors)

        # Update state
        led_state.update(
            mode="gradient_static",
            gradient_config=config.dict(),
            brightness=config.brightness,
            rgb=colors[0] if colors else (0, 0, 0)  # First pixel color
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        logger.info(f"Applied static gradient: {len(req.stops)} stops, brightness={req.brightness}")
        return {
            "status": "ok",
            "mode": "gradient_static",
            "pixel_count": LED_COUNT,
            "stops": len(req.stops)
        }

    except ValueError as e:
        logger.warning(f"Invalid gradient configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to set static gradient", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.post("/gradient/animated")
async def set_gradient_animated(req: GradientAnimatedRequest):
    """
    Start animated gradient.

    Animations:
      - shift: Gradient position shifts along strip
      - pulse: Brightness pulses with sine wave
      - rainbow: Hue rotates over time

    Example:
        {
          "stops": [
            {"position": 0.0, "r": 255, "g": 0, "b": 0},
            {"position": 1.0, "r": 0, "g": 0, "b": 255}
          ],
          "brightness": 1.0,
          "animation": "shift",
          "speed": 1.0,
          "direction": "forward",
          "duration": 60
        }
    """
    try:
        # Create config and validate
        config = GradientConfig(
            stops=req.stops,
            brightness=req.brightness,
            animation=req.animation,
            speed=req.speed,
            direction=req.direction
        )
        validate_gradient_config(config)

        # Start animation in background thread
        animation_name = f"gradient_{req.animation}"
        run_async(
            animation_name,
            animate_gradient,
            leds,
            config,
            req.duration
        )

        # Update state
        led_state.update(
            mode="gradient_animated",
            gradient_config=config.dict(),
            active_animation=animation_name,
            brightness=config.brightness
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        logger.info(f"Started gradient animation: type={req.animation}, duration={req.duration}s, stops={len(req.stops)}")
        return {
            "status": "ok",
            "mode": "gradient_animated",
            "animation": req.animation,
            "duration": req.duration,
            "stops": len(req.stops)
        }

    except ValueError as e:
        logger.warning(f"Invalid gradient configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to start animated gradient", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.post("/gradient/preset/save")
async def save_gradient_preset_endpoint(preset: GradientPreset):
    """
    Save gradient preset for later use.

    Example:
        {
          "name": "my_gradient",
          "description": "Cool blue and purple",
          "config": {
            "stops": [...],
            "brightness": 0.9,
            "animation": null,
            "speed": 1.0,
            "direction": "forward"
          }
        }
    """
    try:
        validate_gradient_config(preset.config)
        save_preset(preset)

        logger.info(f"Saved gradient preset: {preset.name}")
        return {
            "status": "ok",
            "name": preset.name,
            "description": preset.description
        }

    except ValueError as e:
        logger.warning(f"Invalid preset: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to save gradient preset", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.get("/gradient/preset/{name}")
async def load_gradient_preset_endpoint(name: str):
    """Load and apply gradient preset by name."""
    try:
        preset = get_preset(name)

        if not preset:
            raise HTTPException(
                status_code=404,
                detail=f"Preset '{name}' not found. Available presets: {', '.join(list_preset_names())}"
            )

        # Apply preset (static or animated)
        if preset.config.animation:
            # Start animated gradient
            animation_name = f"gradient_{preset.config.animation}"
            run_async(
                animation_name,
                animate_gradient,
                leds,
                preset.config,
                0  # Infinite duration
            )

            led_state.update(
                mode="gradient_animated",
                gradient_config=preset.config.dict(),
                active_animation=animation_name,
                brightness=preset.config.brightness
            )

            # Publish to MQTT
            await publish_state_to_mqtt()

            logger.info(f"Applied animated preset: {name} ({preset.config.animation})")
            return {
                "status": "ok",
                "preset": name,
                "mode": "gradient_animated",
                "animation": preset.config.animation
            }
        else:
            # Apply static gradient
            colors = render_gradient(preset.config.stops, LED_COUNT)
            leds.set_brightness(preset.config.brightness)
            leds.set_pixel_array(colors)

            led_state.update(
                mode="gradient_static",
                gradient_config=preset.config.dict(),
                brightness=preset.config.brightness,
                rgb=colors[0] if colors else (0, 0, 0)
            )

            # Publish to MQTT
            await publish_state_to_mqtt()

            logger.info(f"Applied static preset: {name}")
            return {
                "status": "ok",
                "preset": name,
                "mode": "gradient_static",
                "stops": len(preset.config.stops)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load preset '{name}'", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.delete("/gradient/preset/{name}")
async def delete_gradient_preset_endpoint(name: str):
    """Delete gradient preset by name."""
    try:
        success = delete_preset(name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Preset '{name}' not found"
            )

        logger.info(f"Deleted gradient preset: {name}")
        return {
            "status": "ok",
            "deleted": name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete preset '{name}'", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@backlight_router.get("/gradient/presets")
async def list_gradient_presets_endpoint():
    """List all available gradient presets."""
    try:
        presets = load_presets()

        return {
            "presets": [
                {
                    "name": name,
                    "description": preset.description,
                    "animated": preset.config.animation is not None,
                    "animation_type": preset.config.animation,
                    "stops": len(preset.config.stops)
                }
                for name, preset in presets.items()
            ],
            "count": len(presets)
        }

    except Exception as e:
        logger.error("Failed to list presets", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Temperature sensor endpoints
# ------------------------------------------------------------------

@app.get("/temperature")
async def get_all_temperatures():
    """
    Get temperature readings from all configured sensors.

    Returns:
        {
            "sensors": {
                "28-00000xxxxx": {
                    "celsius": 23.5,
                    "fahrenheit": 74.3,
                    "timestamp": 1234567890.123,
                    "valid": true
                }
            },
            "count": 1,
            "unit": "celsius"
        }
    """
    if not temp_manager:
        raise HTTPException(status_code=503, detail="Temperature sensors not enabled")

    try:
        readings = await asyncio.to_thread(temp_manager.read_all)

        # Convert to JSON-serializable format
        sensors_data = {}
        for sensor_id, reading in readings.items():
            sensors_data[sensor_id] = {
                "celsius": reading.celsius,
                "fahrenheit": reading.fahrenheit,
                "timestamp": reading.timestamp,
                "valid": reading.valid,
                "error": reading.error
            }

        # Update state
        led_state.update(
            temperature_readings=sensors_data,
            last_temp_update=datetime.now()
        )

        # Publish to MQTT
        await publish_state_to_mqtt()

        return {
            "sensors": sensors_data,
            "count": len(sensors_data),
            "unit": TEMP_UNIT
        }

    except Exception as e:
        logger.error("Failed to read temperatures", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temperature/{sensor_id}")
async def get_sensor_temperature(sensor_id: str):
    """
    Get temperature reading from specific sensor.

    Args:
        sensor_id: DS18B20 sensor ID (e.g., '28-00000xxxxx')

    Returns:
        {
            "sensor_id": "28-00000xxxxx",
            "celsius": 23.5,
            "fahrenheit": 74.3,
            "timestamp": 1234567890.123,
            "valid": true,
            "unit": "celsius"
        }
    """
    if not temp_manager:
        raise HTTPException(status_code=503, detail="Temperature sensors not enabled")

    try:
        reading = await asyncio.to_thread(temp_manager.read_sensor, sensor_id)

        if not reading:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")

        return {
            "sensor_id": reading.sensor_id,
            "celsius": reading.celsius,
            "fahrenheit": reading.fahrenheit,
            "timestamp": reading.timestamp,
            "valid": reading.valid,
            "error": reading.error,
            "unit": TEMP_UNIT
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read sensor {sensor_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temperature/sensors/discover")
async def discover_temperature_sensors():
    """
    Discover all DS18B20 sensors on 1-Wire bus.

    Returns:
        {
            "sensors": ["28-00000xxxxx", "28-00000yyyyy"],
            "count": 2
        }
    """
    if not temp_manager:
        raise HTTPException(status_code=503, detail="Temperature sensors not enabled")

    try:
        sensor_ids = await asyncio.to_thread(temp_manager.refresh_sensors)

        return {
            "sensors": sensor_ids,
            "count": len(sensor_ids)
        }

    except Exception as e:
        logger.error("Failed to discover sensors", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temperature/sensors/list")
async def list_temperature_sensors():
    """
    List currently configured temperature sensors.

    Returns:
        {
            "sensors": ["28-00000xxxxx"],
            "count": 1
        }
    """
    if not temp_manager:
        raise HTTPException(status_code=503, detail="Temperature sensors not enabled")

    try:
        sensor_ids = temp_manager.get_sensor_ids()

        return {
            "sensors": sensor_ids,
            "count": len(sensor_ids)
        }

    except Exception as e:
        logger.error("Failed to list sensors", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# State
# ------------------------------------------------------------------

@backlight_router.get("/state")
async def get_state():
    """
    Get current LED state.

    Useful for:
    - Debugging
    - MQTT synchronization
    - UI state updates
    """
    try:
        return led_state.get_snapshot()
    except Exception as e:
        logger.error("Failed to get state", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Register Routers
# ============================================================================

app.include_router(backlight_router)

