"""
Gradient rendering engine for LED strip.

Supports:
- Static gradients (2-color and multi-color)
- Animated gradients (shift, pulse, rainbow)
- Color interpolation with smooth transitions
"""

import time
import colorsys
import math
import threading
from typing import Literal
from pydantic import BaseModel, Field

from app.config import ANIMATION_FPS
from app.logger import logger


# ============================================================================
# Data Structures
# ============================================================================

class ColorStop(BaseModel):
    """Single color stop in a gradient."""
    position: float = Field(..., ge=0.0, le=1.0, description="Position along gradient (0.0-1.0)")
    r: int = Field(..., ge=0, le=255, description="Red component (0-255)")
    g: int = Field(..., ge=0, le=255, description="Green component (0-255)")
    b: int = Field(..., ge=0, le=255, description="Blue component (0-255)")

    class Config:
        frozen = True  # Make immutable for hashing


class GradientConfig(BaseModel):
    """Complete gradient configuration."""
    stops: list[ColorStop] = Field(..., min_items=2, description="At least 2 color stops required")
    brightness: float = Field(1.0, ge=0.0, le=1.0, description="Global brightness (0.0-1.0)")

    # Animation parameters (None = static)
    animation: Literal["shift", "pulse", "rainbow"] | None = None
    speed: float = Field(1.0, gt=0.0, description="Animation speed multiplier")
    direction: Literal["forward", "backward"] = "forward"


# ============================================================================
# Gradient Rendering
# ============================================================================

def render_gradient(stops: list[ColorStop], pixel_count: int, offset: float = 0.0) -> list[tuple[int, int, int]]:
    """
    Render gradient to pixel array with linear interpolation.

    Args:
        stops: List of ColorStop objects (must be at least 2)
        pixel_count: Number of pixels to generate
        offset: Position offset for animation (0.0-1.0, wraps around)

    Returns:
        List of (r, g, b) tuples, one per pixel

    Algorithm:
        1. Sort stops by position
        2. For each pixel i:
           - Calculate position t = (i / (pixel_count - 1) + offset) % 1.0
           - Find surrounding stops
           - Linear interpolate RGB between stops

    Example:
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),   # Red
            ColorStop(position=1.0, r=0, g=0, b=255)    # Blue
        ]
        colors = render_gradient(stops, 10)
        # Returns: [(255,0,0), (227,0,28), ..., (0,0,255)]
    """
    if len(stops) < 2:
        raise ValueError("At least 2 color stops required")

    if pixel_count <= 0:
        return []

    # Sort stops by position
    sorted_stops = sorted(stops, key=lambda s: s.position)

    colors = []

    for i in range(pixel_count):
        # Calculate position with offset (wraps around)
        if pixel_count == 1:
            t = 0.0
        else:
            t = i / (pixel_count - 1) + offset
            # Only wrap if offset is non-zero (for animations)
            if offset != 0.0:
                t = t % 1.0

        # Find surrounding stops
        left_stop = sorted_stops[0]
        right_stop = sorted_stops[-1]

        for j in range(len(sorted_stops) - 1):
            if sorted_stops[j].position <= t <= sorted_stops[j + 1].position:
                left_stop = sorted_stops[j]
                right_stop = sorted_stops[j + 1]
                break

        # Calculate interpolation factor
        if right_stop.position == left_stop.position:
            factor = 0.0
        else:
            factor = (t - left_stop.position) / (right_stop.position - left_stop.position)

        # Linear interpolate RGB
        r = int(left_stop.r + (right_stop.r - left_stop.r) * factor)
        g = int(left_stop.g + (right_stop.g - left_stop.g) * factor)
        b = int(left_stop.b + (right_stop.b - left_stop.b) * factor)

        # Clamp to valid range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        colors.append((r, g, b))

    return colors


# ============================================================================
# Animated Gradients
# ============================================================================

def animate_gradient(leds, config: GradientConfig, duration: int, cancel_event: threading.Event):
    """
    Animate gradient on LED strip.

    Args:
        leds: LedStrip instance
        config: GradientConfig with animation settings
        duration: Animation duration in seconds (0 = infinite)
        cancel_event: Threading event for cancellation

    Animations:
        - shift: Gradient position shifts along strip
        - pulse: Brightness pulses with sine wave
        - rainbow: Hue rotates over time (HSV space)
    """
    logger.info(f"Starting gradient animation: type={config.animation}, duration={duration}s, speed={config.speed}")

    if config.animation == "shift":
        _animate_shift(leds, config, duration, cancel_event)
    elif config.animation == "pulse":
        _animate_pulse(leds, config, duration, cancel_event)
    elif config.animation == "rainbow":
        _animate_rainbow(leds, config, duration, cancel_event)
    else:
        logger.warning(f"Unknown animation type: {config.animation}")


def _animate_shift(leds, config: GradientConfig, duration: int, cancel_event: threading.Event):
    """Shift gradient position along LED strip."""
    start_time = time.time()
    frame = 0

    with leds.anim_lock:
        while True:
            # Check cancellation
            if cancel_event.is_set():
                logger.info("Gradient shift animation cancelled")
                return

            # Check duration
            if duration > 0 and (time.time() - start_time) >= duration:
                logger.info("Gradient shift animation completed")
                return

            # Calculate offset (0.0-1.0, wraps around)
            offset = (frame * config.speed * 0.01) % 1.0

            # Reverse direction if needed
            if config.direction == "backward":
                offset = 1.0 - offset

            # Render gradient with offset
            colors = render_gradient(config.stops, leds.count, offset)

            # Apply to LEDs
            try:
                leds.set_brightness(config.brightness)
                leds.set_pixel_array(colors)
            except Exception as e:
                logger.error("Error rendering gradient shift", exc_info=True)
                raise

            # Sleep for frame timing
            time.sleep(1 / ANIMATION_FPS)
            frame += 1


def _animate_pulse(leds, config: GradientConfig, duration: int, cancel_event: threading.Event):
    """Pulse gradient brightness with sine wave."""
    start_time = time.time()
    frame = 0

    # Pre-render static gradient
    colors = render_gradient(config.stops, leds.count)

    with leds.anim_lock:
        while True:
            # Check cancellation
            if cancel_event.is_set():
                logger.info("Gradient pulse animation cancelled")
                return

            # Check duration
            if duration > 0 and (time.time() - start_time) >= duration:
                logger.info("Gradient pulse animation completed")
                return

            # Calculate brightness multiplier (sine wave 0.3-1.0)
            t = frame * config.speed * 0.05
            brightness_mult = 0.3 + 0.7 * (math.sin(t) * 0.5 + 0.5)
            brightness = config.brightness * brightness_mult

            # Apply to LEDs
            try:
                leds.set_brightness(brightness)
                leds.set_pixel_array(colors)
            except Exception as e:
                logger.error("Error rendering gradient pulse", exc_info=True)
                raise

            # Sleep for frame timing
            time.sleep(1 / ANIMATION_FPS)
            frame += 1


def _animate_rainbow(leds, config: GradientConfig, duration: int, cancel_event: threading.Event):
    """Rotate hue values over time (rainbow effect)."""
    start_time = time.time()
    frame = 0

    with leds.anim_lock:
        while True:
            # Check cancellation
            if cancel_event.is_set():
                logger.info("Gradient rainbow animation cancelled")
                return

            # Check duration
            if duration > 0 and (time.time() - start_time) >= duration:
                logger.info("Gradient rainbow animation completed")
                return

            # Generate rainbow gradient
            colors = []
            hue_offset = (frame * config.speed * 0.01) % 1.0

            for i in range(leds.count):
                # Calculate hue (0.0-1.0)
                hue = (i / leds.count + hue_offset) % 1.0

                # Reverse direction if needed
                if config.direction == "backward":
                    hue = 1.0 - hue

                # Convert HSV to RGB
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                colors.append((int(r * 255), int(g * 255), int(b * 255)))

            # Apply to LEDs
            try:
                leds.set_brightness(config.brightness)
                leds.set_pixel_array(colors)
            except Exception as e:
                logger.error("Error rendering gradient rainbow", exc_info=True)
                raise

            # Sleep for frame timing
            time.sleep(1 / ANIMATION_FPS)
            frame += 1


# ============================================================================
# Validation
# ============================================================================

def validate_gradient_config(config: GradientConfig) -> None:
    """
    Validate gradient configuration.

    Raises:
        ValueError: If configuration is invalid

    Checks:
        - At least 2 color stops
        - Stops in ascending position order
        - Valid RGB values (0-255)
        - Valid brightness (0.0-1.0)
    """
    if len(config.stops) < 2:
        raise ValueError("At least 2 color stops required")

    # Check stops are in order
    positions = [stop.position for stop in config.stops]
    if positions != sorted(positions):
        raise ValueError("Color stops must be in ascending position order")

    # Check for duplicate positions
    if len(positions) != len(set(positions)):
        raise ValueError("Duplicate color stop positions not allowed")

    # Pydantic already validates RGB (0-255) and brightness (0.0-1.0)
    # via Field constraints, so no need to check here
