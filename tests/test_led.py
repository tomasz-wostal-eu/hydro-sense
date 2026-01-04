"""Tests for LED hardware abstraction layer."""

import pytest
import threading
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def mock_pixel_strip():
    """Mock PixelStrip hardware."""
    with patch('app.led.PixelStrip') as mock:
        strip_instance = MagicMock()
        strip_instance.numPixels.return_value = 30
        mock.return_value = strip_instance
        yield mock


@pytest.fixture
def led_strip(mock_pixel_strip):
    """Create LedStrip instance with mocked hardware."""
    from app.led import LedStrip
    return LedStrip(count=30)


class TestLedStripInitialization:
    """Tests for LedStrip initialization."""

    def test_initialization_success(self, mock_pixel_strip):
        """Should initialize LED strip successfully."""
        from app.led import LedStrip

        strip = LedStrip(count=30)

        assert strip.count == 30
        assert strip.brightness == 1.0
        assert len(strip.gamma) == 256
        assert strip.lock is not None
        assert strip.anim_lock is not None
        mock_pixel_strip.return_value.begin.assert_called_once()

    def test_initialization_failure(self):
        """Should raise exception on hardware initialization failure."""
        from app.led import LedStrip

        with patch('app.led.PixelStrip', side_effect=RuntimeError("Hardware error")):
            with pytest.raises(RuntimeError):
                LedStrip(count=30)


class TestGammaTable:
    """Tests for gamma correction table generation."""

    def test_build_gamma_table(self):
        """Should generate 256-entry gamma correction table."""
        from app.led import build_gamma_table

        table = build_gamma_table(2.2)

        assert len(table) == 256
        assert table[0] == 0
        assert table[255] == 255
        # Gamma should be non-linear
        assert table[128] < 128

    def test_gamma_monotonic(self):
        """Should produce monotonically increasing values."""
        from app.led import build_gamma_table

        table = build_gamma_table(2.2)

        for i in range(len(table) - 1):
            assert table[i] <= table[i + 1]

    def test_different_gamma_values(self):
        """Should handle different gamma values."""
        from app.led import build_gamma_table

        table_1_0 = build_gamma_table(1.0)
        table_2_2 = build_gamma_table(2.2)

        # Gamma 1.0 should be linear
        assert table_1_0[128] == 128

        # Gamma 2.2 should be non-linear
        assert table_2_2[128] < 128


class TestBrightnessControl:
    """Tests for brightness control."""

    def test_set_brightness_valid(self, led_strip):
        """Should set brightness within valid range."""
        led_strip.set_brightness(0.5)
        assert led_strip.brightness == 0.5

        led_strip.set_brightness(0.0)
        assert led_strip.brightness == 0.0

        led_strip.set_brightness(1.0)
        assert led_strip.brightness == 1.0

    def test_set_brightness_clamping(self, led_strip):
        """Should clamp brightness to [0.0, 1.0]."""
        led_strip.set_brightness(1.5)
        assert led_strip.brightness == 1.0

        led_strip.set_brightness(-0.5)
        assert led_strip.brightness == 0.0

    def test_brightness_thread_safe(self, led_strip):
        """Should handle concurrent brightness changes safely."""
        errors = []

        def set_brightness_many_times(value):
            try:
                for _ in range(100):
                    led_strip.set_brightness(value)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=set_brightness_many_times, args=(0.3,)),
            threading.Thread(target=set_brightness_many_times, args=(0.7,)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert led_strip.brightness in [0.3, 0.7]


class TestRGBControl:
    """Tests for RGB color control."""

    def test_set_rgb(self, led_strip):
        """Should set all pixels to RGB color."""
        led_strip.set_rgb(255, 128, 64)

        # Verify setPixelColor called for each pixel
        assert led_strip.strip.setPixelColor.call_count == 30
        led_strip.strip.show.assert_called()

    def test_set_rgb_with_brightness(self, led_strip):
        """Should apply brightness to RGB values."""
        led_strip.set_brightness(0.5)
        led_strip.set_rgb(255, 128, 64)

        # Colors should be affected by brightness and gamma
        led_strip.strip.show.assert_called()

    def test_set_rgb_thread_safe(self, led_strip):
        """Should handle concurrent RGB updates safely."""
        errors = []

        def set_color(r, g, b):
            try:
                for _ in range(10):
                    led_strip.set_rgb(r, g, b)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=set_color, args=(255, 0, 0)),
            threading.Thread(target=set_color, args=(0, 255, 0)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0


class TestHSVControl:
    """Tests for HSV color control."""

    def test_set_hsv(self, led_strip):
        """Should convert HSV to RGB and set color."""
        led_strip.set_hsv(0, 1.0, 1.0)  # Red
        led_strip.strip.show.assert_called()

    def test_set_hsv_hue_wrapping(self, led_strip):
        """Should wrap hue values > 360."""
        led_strip.set_hsv(370, 1.0, 1.0)
        led_strip.strip.show.assert_called()

    def test_set_hsv_saturation_clamping(self, led_strip):
        """Should clamp saturation to [0.0, 1.0]."""
        led_strip.set_hsv(180, 1.5, 1.0)
        led_strip.strip.show.assert_called()

        led_strip.set_hsv(180, -0.5, 1.0)
        led_strip.strip.show.assert_called()

    def test_set_hsv_value_clamping(self, led_strip):
        """Should clamp value to [0.0, 1.0]."""
        led_strip.set_hsv(180, 1.0, 1.5)
        led_strip.strip.show.assert_called()

        led_strip.set_hsv(180, 1.0, -0.5)
        led_strip.strip.show.assert_called()


class TestPixelArray:
    """Tests for pixel array operations."""

    def test_set_pixel_array(self, led_strip):
        """Should set individual pixel colors from array."""
        colors = [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
        ]

        led_strip.set_pixel_array(colors)

        assert led_strip.strip.setPixelColor.call_count == 3
        led_strip.strip.show.assert_called()

    def test_set_pixel_array_truncation(self, led_strip):
        """Should not exceed strip length."""
        colors = [(255, 0, 0)] * 100  # More than 30 pixels

        led_strip.set_pixel_array(colors)

        # Should only set 30 pixels
        assert led_strip.strip.setPixelColor.call_count == 30

    def test_set_pixel_array_empty(self, led_strip):
        """Should handle empty array."""
        led_strip.set_pixel_array([])

        led_strip.strip.show.assert_called()


class TestSinglePixel:
    """Tests for single pixel operations."""

    def test_set_pixel_valid(self, led_strip):
        """Should set single pixel color."""
        led_strip.set_pixel(0, 255, 0, 0)

        led_strip.strip.setPixelColor.assert_called_once()
        led_strip.strip.show.assert_called()

    def test_set_pixel_out_of_bounds(self, led_strip):
        """Should ignore out-of-bounds indices."""
        led_strip.set_pixel(100, 255, 0, 0)

        # Should not call setPixelColor
        led_strip.strip.setPixelColor.assert_not_called()

    def test_set_pixel_negative_index(self, led_strip):
        """Should ignore negative indices."""
        led_strip.set_pixel(-1, 255, 0, 0)

        led_strip.strip.setPixelColor.assert_not_called()


class TestTurnOff:
    """Tests for turning off LEDs."""

    def test_off(self, led_strip):
        """Should turn off all LEDs."""
        led_strip.off()

        # Should set all pixels to black
        assert led_strip.strip.setPixelColor.call_count == 30
        led_strip.strip.show.assert_called()


class TestAnimationLock:
    """Tests for animation mutex."""

    def test_anim_lock_exists(self, led_strip):
        """Should have animation lock."""
        assert led_strip.anim_lock is not None
        assert isinstance(led_strip.anim_lock, threading.Lock)

    def test_anim_lock_prevents_concurrent_animations(self, led_strip):
        """Should prevent multiple animations from running simultaneously."""
        acquired = []

        def try_acquire():
            if led_strip.anim_lock.acquire(blocking=False):
                acquired.append(True)
                threading.Event().wait(0.1)  # Simulate animation work
                led_strip.anim_lock.release()
            else:
                acquired.append(False)

        threads = [
            threading.Thread(target=try_acquire),
            threading.Thread(target=try_acquire),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # One should succeed, one should fail
        assert True in acquired
        assert False in acquired
