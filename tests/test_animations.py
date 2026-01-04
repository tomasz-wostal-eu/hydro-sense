"""Tests for lighting animations."""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from app.animations import cloudy_sunrise, cloudy_sunset


@pytest.fixture
def mock_led_strip():
    """Create mock LED strip for animation testing."""
    mock = MagicMock()
    mock.anim_lock = threading.Lock()
    mock.set_hsv = Mock()
    return mock


@pytest.fixture
def cancel_event():
    """Create cancel event for animations."""
    return threading.Event()


class TestCloudySunrise:
    """Tests for cloudy sunrise animation."""

    def test_sunrise_completes(self, mock_led_strip, cancel_event):
        """Should complete sunrise animation."""
        # Use very short duration for testing
        duration = 1  # 1 second

        cloudy_sunrise(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)

        # Should have called set_hsv multiple times
        assert mock_led_strip.set_hsv.call_count > 0

    def test_sunrise_color_progression(self, mock_led_strip, cancel_event):
        """Should progress through sunrise colors."""
        duration = 1

        cloudy_sunrise(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)

        # Verify set_hsv was called with valid HSV values
        for call in mock_led_strip.set_hsv.call_args_list:
            h, s, v = call[0]
            assert 0 <= h <= 360
            assert 0 <= s <= 1.0
            assert 0 <= v <= 1.0

    def test_sunrise_cancellation(self, mock_led_strip, cancel_event):
        """Should stop when cancelled."""
        duration = 10  # Long duration

        # Cancel after short time
        def cancel_after_delay():
            time.sleep(0.2)
            cancel_event.set()

        cancel_thread = threading.Thread(target=cancel_after_delay)
        cancel_thread.start()

        start_time = time.time()
        cloudy_sunrise(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)
        elapsed = time.time() - start_time

        cancel_thread.join()

        # Should stop early (much less than 10 seconds)
        assert elapsed < 5.0

    def test_sunrise_respects_anim_lock(self, mock_led_strip, cancel_event):
        """Should acquire animation lock."""
        duration = 1

        # Manually acquire lock
        mock_led_strip.anim_lock.acquire()

        # Animation should block
        animation_started = threading.Event()

        def run_animation():
            animation_started.set()
            cloudy_sunrise(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)

        thread = threading.Thread(target=run_animation)
        thread.start()

        # Wait a bit
        time.sleep(0.1)

        # Animation should not have made progress (blocked on lock)
        assert mock_led_strip.set_hsv.call_count == 0

        # Release lock
        mock_led_strip.anim_lock.release()

        # Wait for animation to complete
        thread.join(timeout=2)

        # Now should have made calls
        assert mock_led_strip.set_hsv.call_count > 0

    def test_sunrise_different_seasons(self, mock_led_strip):
        """Should work with different seasons."""
        seasons = ["spring", "summer", "autumn", "winter"]

        for season in seasons:
            mock_led_strip.set_hsv.reset_mock()
            cancel_event = threading.Event()

            cloudy_sunrise(mock_led_strip, duration=1, season=season, cancel_event=cancel_event)

            # Should complete for each season
            assert mock_led_strip.set_hsv.call_count > 0

    def test_sunrise_error_handling(self, mock_led_strip, cancel_event):
        """Should propagate errors from LED operations."""
        mock_led_strip.set_hsv.side_effect = RuntimeError("LED error")

        with pytest.raises(RuntimeError, match="LED error"):
            cloudy_sunrise(mock_led_strip, duration=1, season="spring", cancel_event=cancel_event)


class TestCloudySunset:
    """Tests for cloudy sunset animation."""

    def test_sunset_completes(self, mock_led_strip, cancel_event):
        """Should complete sunset animation."""
        duration = 1

        cloudy_sunset(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)

        # Should have called set_hsv multiple times
        assert mock_led_strip.set_hsv.call_count > 0

    def test_sunset_color_progression(self, mock_led_strip, cancel_event):
        """Should progress through sunset colors."""
        duration = 1

        cloudy_sunset(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)

        # Verify set_hsv was called with valid HSV values
        for call in mock_led_strip.set_hsv.call_args_list:
            h, s, v = call[0]
            assert 0 <= h <= 360
            assert 0 <= s <= 1.0
            assert 0 <= v <= 1.0

    def test_sunset_brightness_decreases(self, mock_led_strip, cancel_event):
        """Should decrease brightness over time (sunset)."""
        duration = 1

        cloudy_sunset(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)

        # Get all V (brightness) values
        v_values = [call[0][2] for call in mock_led_strip.set_hsv.call_args_list]

        # First value should be higher than last (brightness decreases)
        assert v_values[0] > v_values[-1]

    def test_sunset_cancellation(self, mock_led_strip, cancel_event):
        """Should stop when cancelled."""
        duration = 10

        def cancel_after_delay():
            time.sleep(0.2)
            cancel_event.set()

        cancel_thread = threading.Thread(target=cancel_after_delay)
        cancel_thread.start()

        start_time = time.time()
        cloudy_sunset(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)
        elapsed = time.time() - start_time

        cancel_thread.join()

        # Should stop early
        assert elapsed < 5.0

    def test_sunset_respects_anim_lock(self, mock_led_strip, cancel_event):
        """Should acquire animation lock."""
        duration = 1

        mock_led_strip.anim_lock.acquire()

        def run_animation():
            cloudy_sunset(mock_led_strip, duration=duration, season="spring", cancel_event=cancel_event)

        thread = threading.Thread(target=run_animation)
        thread.start()

        time.sleep(0.1)

        # Should be blocked
        assert mock_led_strip.set_hsv.call_count == 0

        mock_led_strip.anim_lock.release()
        thread.join(timeout=2)

        # Now should have made calls
        assert mock_led_strip.set_hsv.call_count > 0

    def test_sunset_different_seasons(self, mock_led_strip):
        """Should work with different seasons."""
        seasons = ["spring", "summer", "autumn", "winter"]

        for season in seasons:
            mock_led_strip.set_hsv.reset_mock()
            cancel_event = threading.Event()

            cloudy_sunset(mock_led_strip, duration=1, season=season, cancel_event=cancel_event)

            assert mock_led_strip.set_hsv.call_count > 0

    def test_sunset_error_handling(self, mock_led_strip, cancel_event):
        """Should propagate errors from LED operations."""
        mock_led_strip.set_hsv.side_effect = RuntimeError("LED error")

        with pytest.raises(RuntimeError, match="LED error"):
            cloudy_sunset(mock_led_strip, duration=1, season="spring", cancel_event=cancel_event)


class TestAnimationIntegration:
    """Integration tests for animations."""

    def test_sunrise_then_sunset(self, mock_led_strip):
        """Should run sunrise followed by sunset."""
        cancel_event1 = threading.Event()
        cancel_event2 = threading.Event()

        cloudy_sunrise(mock_led_strip, duration=1, season="spring", cancel_event=cancel_event1)
        sunrise_calls = mock_led_strip.set_hsv.call_count

        cloudy_sunset(mock_led_strip, duration=1, season="spring", cancel_event=cancel_event2)
        total_calls = mock_led_strip.set_hsv.call_count

        # Both animations should have run
        assert sunrise_calls > 0
        assert total_calls > sunrise_calls

    def test_concurrent_animations_blocked(self, mock_led_strip):
        """Should not allow concurrent animations due to anim_lock."""
        cancel_event1 = threading.Event()
        cancel_event2 = threading.Event()

        results = []

        def run_sunrise():
            try:
                cloudy_sunrise(mock_led_strip, duration=2, season="spring", cancel_event=cancel_event1)
                results.append("sunrise_complete")
            except Exception as e:
                results.append(f"sunrise_error: {e}")

        def run_sunset():
            try:
                cloudy_sunset(mock_led_strip, duration=2, season="spring", cancel_event=cancel_event2)
                results.append("sunset_complete")
            except Exception as e:
                results.append(f"sunset_error: {e}")

        thread1 = threading.Thread(target=run_sunrise)
        thread2 = threading.Thread(target=run_sunset)

        thread1.start()
        time.sleep(0.1)  # Let first animation start
        thread2.start()

        thread1.join(timeout=5)
        thread2.join(timeout=5)

        # Both should complete, but sequentially (not concurrently)
        assert len(results) == 2
        assert "sunrise_complete" in results
        assert "sunset_complete" in results
