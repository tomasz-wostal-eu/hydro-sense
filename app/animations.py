"""
High-level lighting animations.

All animations:
- Are blocking
- Must run in a background thread
- Are protected by anim_lock
- Support cancellation via threading.Event
"""

import time
import threading
from app.lighting_math import smoothstep, lerp, SmoothNoise
from app.season_profiles import SEASONS
from app.config import ANIMATION_FPS
from app.logger import logger

FPS = ANIMATION_FPS


def cloudy_sunrise(leds, duration: int, season: str, cancel_event: threading.Event):
    logger.info(f"Starting cloudy_sunrise: duration={duration}s, season={season}")

    profile = SEASONS[season]["sunrise"]
    max_v = SEASONS[season]["max_v"]
    noise = SmoothNoise(SEASONS[season]["cloud_intensity"])

    with leds.anim_lock:
        steps = duration * FPS
        for i in range(steps + 1):
            # Check for cancellation
            if cancel_event.is_set():
                logger.info("Animation cancelled: cloudy_sunrise")
                return

            t = smoothstep(i / steps)

            h = lerp(profile["h_start"], profile["h_end"], t)
            s = lerp(profile["s_start"], profile["s_end"], t)

            base_v = lerp(0.01, max_v, t)

            # Disable clouds when very dark (human eye is sensitive here)
            if base_v < 0.15:
                v = base_v
            else:
                v = base_v + noise.step(1 / FPS)

            v = max(0.01, min(max_v, v))

            try:
                leds.set_hsv(h, s, v)
            except Exception as e:
                logger.error("Error setting LED color", exc_info=True)
                raise

            time.sleep(1 / FPS)

    logger.info("Animation completed: cloudy_sunrise")


def cloudy_sunset(leds, duration: int, season: str, cancel_event: threading.Event):
    logger.info(f"Starting cloudy_sunset: duration={duration}s, season={season}")

    profile = SEASONS[season]["sunset"]
    max_v = SEASONS[season]["max_v"]
    noise = SmoothNoise(SEASONS[season]["cloud_intensity"])

    with leds.anim_lock:
        steps = duration * FPS
        for i in range(steps + 1):
            # Check for cancellation
            if cancel_event.is_set():
                logger.info("Animation cancelled: cloudy_sunset")
                return

            t = smoothstep(i / steps)

            h = lerp(profile["h_start"], profile["h_end"], t)
            s = lerp(profile["s_start"], profile["s_end"], t)

            base_v = lerp(max_v, 0.01, t)

            if base_v < 0.15:
                v = base_v
            else:
                v = base_v + noise.step(1 / FPS)

            v = max(0.01, min(max_v, v))

            try:
                leds.set_hsv(h, s, v)
            except Exception as e:
                logger.error("Error setting LED color", exc_info=True)
                raise

            time.sleep(1 / FPS)

    logger.info("Animation completed: cloudy_sunset")

