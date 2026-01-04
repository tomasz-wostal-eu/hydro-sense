"""
LED hardware abstraction layer.

Features:
- WS2813 via DMA (rpi_ws281x)
- HSV input
- Global brightness
- Gamma correction
- Thread-safe access
- Animation mutex (only one animation at a time)
"""

from rpi_ws281x import PixelStrip, Color
import threading
import colorsys

from app.config import LED_PIN, LED_FREQ_HZ, LED_DMA, LED_CHANNEL, LED_GAMMA
from app.logger import logger


def build_gamma_table(gamma: float):
    """Generate gamma correction lookup table."""
    return [int(pow(i / 255.0, gamma) * 255.0 + 0.5) for i in range(256)]


class LedStrip:
    def __init__(self, count: int):
        try:
            logger.info(f"Initializing LED strip: count={count}, pin={LED_PIN}, dma={LED_DMA}")
            self.count = count
            self.brightness = 1.0
            self.gamma = build_gamma_table(LED_GAMMA)

            self.strip = PixelStrip(
                count,
                LED_PIN,
                LED_FREQ_HZ,
                LED_DMA,
                False,
                255,
                LED_CHANNEL,
            )
            self.strip.begin()
            logger.info("LED strip initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize LED hardware", exc_info=True)
            raise

        # Prevent concurrent hardware access
        self.lock = threading.Lock()

        # Ensure only ONE animation runs at a time
        self.anim_lock = threading.Lock()

    # -------------------------------------------------------------

    def set_brightness(self, level: float):
        with self.lock:
            self.brightness = max(0.0, min(1.0, level))

    def _apply_pipeline(self, r: int, g: int, b: int) -> Color:
        r = self.gamma[int(r * self.brightness)]
        g = self.gamma[int(g * self.brightness)]
        b = self.gamma[int(b * self.brightness)]
        return Color(r, g, b)

    # -------------------------------------------------------------

    def set_rgb(self, r: int, g: int, b: int):
        with self.lock:
            color = self._apply_pipeline(r, g, b)
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, color)
            self.strip.show()

    def set_hsv(self, h: float, s: float, v: float):
        h = (h % 360) / 360.0
        s = max(0.0, min(1.0, s))
        v = max(0.0, min(1.0, v))

        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        self.set_rgb(int(r * 255), int(g * 255), int(b * 255))

    def off(self):
        with self.lock:
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()

    def set_pixel_array(self, colors: list[tuple[int, int, int]]):
        """
        Set individual pixel colors from array (for gradient rendering).

        Args:
            colors: List of (r, g, b) tuples, one per pixel

        Example:
            # Set gradient from red to blue
            colors = [(255, 0, 0), (200, 0, 55), (150, 0, 105), ..., (0, 0, 255)]
            leds.set_pixel_array(colors)
        """
        with self.lock:
            for i, (r, g, b) in enumerate(colors):
                if i >= self.strip.numPixels():
                    break
                color = self._apply_pipeline(r, g, b)
                self.strip.setPixelColor(i, color)
            self.strip.show()

    def set_pixel(self, index: int, r: int, g: int, b: int):
        """
        Set single pixel color (for advanced animations).

        Args:
            index: Pixel index (0-based)
            r: Red (0-255)
            g: Green (0-255)
            b: Blue (0-255)

        Example:
            leds.set_pixel(0, 255, 0, 0)  # First pixel red
        """
        with self.lock:
            if 0 <= index < self.strip.numPixels():
                color = self._apply_pipeline(r, g, b)
                self.strip.setPixelColor(index, color)
                self.strip.show()

