"""Tests for gradient rendering and validation."""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock
from app.gradient import (
    ColorStop,
    GradientConfig,
    render_gradient,
    validate_gradient_config
)


class TestColorStop:
    """Tests for ColorStop model."""

    def test_valid_color_stop(self):
        """Should create valid color stop."""
        stop = ColorStop(position=0.5, r=255, g=128, b=64)
        assert stop.position == 0.5
        assert stop.r == 255
        assert stop.g == 128
        assert stop.b == 64

    def test_position_bounds(self):
        """Should enforce position bounds [0.0, 1.0]."""
        with pytest.raises(ValueError):
            ColorStop(position=-0.1, r=0, g=0, b=0)

        with pytest.raises(ValueError):
            ColorStop(position=1.1, r=0, g=0, b=0)

    def test_rgb_bounds(self):
        """Should enforce RGB bounds [0, 255]."""
        with pytest.raises(ValueError):
            ColorStop(position=0.5, r=-1, g=0, b=0)

        with pytest.raises(ValueError):
            ColorStop(position=0.5, r=0, g=256, b=0)

        with pytest.raises(ValueError):
            ColorStop(position=0.5, r=0, g=0, b=300)

    def test_immutability(self):
        """Should be immutable (frozen)."""
        stop = ColorStop(position=0.5, r=255, g=0, b=0)
        with pytest.raises(Exception):
            stop.position = 0.8


class TestGradientConfig:
    """Tests for GradientConfig model."""

    def test_valid_gradient_config(self):
        """Should create valid gradient configuration."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]
        config = GradientConfig(stops=stops)

        assert len(config.stops) == 2
        assert config.brightness == 1.0
        assert config.animation is None
        assert config.speed == 1.0
        assert config.direction == "forward"

    def test_minimum_stops_required(self):
        """Should require at least 2 color stops."""
        with pytest.raises(ValueError):
            GradientConfig(stops=[ColorStop(position=0.0, r=0, g=0, b=0)])

    def test_brightness_bounds(self):
        """Should enforce brightness bounds [0.0, 1.0]."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]

        with pytest.raises(ValueError):
            GradientConfig(stops=stops, brightness=-0.1)

        with pytest.raises(ValueError):
            GradientConfig(stops=stops, brightness=1.1)

    def test_valid_animations(self):
        """Should accept valid animation types."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]

        for animation in ["shift", "pulse", "rainbow", None]:
            config = GradientConfig(stops=stops, animation=animation)
            assert config.animation == animation

    def test_speed_positive(self):
        """Should require positive speed."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]

        with pytest.raises(ValueError):
            GradientConfig(stops=stops, speed=0.0)

        with pytest.raises(ValueError):
            GradientConfig(stops=stops, speed=-1.0)


class TestRenderGradient:
    """Tests for gradient rendering."""

    def test_two_color_gradient(self):
        """Should render simple two-color gradient."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),  # Red
            ColorStop(position=1.0, r=0, g=0, b=255)   # Blue
        ]

        colors = render_gradient(stops, pixel_count=5)

        assert len(colors) == 5
        assert colors[0] == (255, 0, 0)  # Start: red
        assert colors[4] == (0, 0, 255)  # End: blue
        # Middle colors should be interpolated
        assert 0 < colors[2][0] < 255
        assert 0 < colors[2][2] < 255

    def test_three_color_gradient(self):
        """Should render multi-color gradient with intermediate stops."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),    # Red
            ColorStop(position=0.5, r=0, g=255, b=0),    # Green
            ColorStop(position=1.0, r=0, g=0, b=255)     # Blue
        ]

        colors = render_gradient(stops, pixel_count=9)

        assert len(colors) == 9
        assert colors[0] == (255, 0, 0)  # Red
        assert colors[8] == (0, 0, 255)  # Blue
        # Middle should be close to green
        middle = colors[4]
        assert middle[1] > middle[0] and middle[1] > middle[2]

    def test_gradient_with_offset(self):
        """Should shift gradient with offset parameter."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]

        colors_no_offset = render_gradient(stops, pixel_count=10, offset=0.0)
        colors_with_offset = render_gradient(stops, pixel_count=10, offset=0.5)

        # With offset, colors should be shifted
        assert colors_no_offset != colors_with_offset

    def test_offset_wraps_around(self):
        """Should wrap offset values > 1.0."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]

        colors_offset_0 = render_gradient(stops, pixel_count=10, offset=0.0)
        colors_offset_1 = render_gradient(stops, pixel_count=10, offset=1.0)

        # offset=1.0 should start from same color as offset=0.0
        # First pixel should be the same
        assert colors_offset_0[0] == colors_offset_1[0]

        # Both should start with red
        assert colors_offset_0[0] == (255, 0, 0)
        assert colors_offset_1[0] == (255, 0, 0)

    def test_single_pixel(self):
        """Should handle single pixel case."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]

        colors = render_gradient(stops, pixel_count=1)

        assert len(colors) == 1
        # Should use first color
        assert colors[0] == (255, 0, 0)

    def test_zero_pixels(self):
        """Should return empty list for zero pixels."""
        stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=1.0, r=0, g=0, b=255)
        ]

        colors = render_gradient(stops, pixel_count=0)

        assert colors == []

    def test_rgb_clamping(self):
        """Should clamp RGB values to valid range [0, 255]."""
        stops = [
            ColorStop(position=0.0, r=255, g=255, b=255),
            ColorStop(position=1.0, r=0, g=0, b=0)
        ]

        colors = render_gradient(stops, pixel_count=10)

        for r, g, b in colors:
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255

    def test_unsorted_stops(self):
        """Should handle unsorted color stops by sorting them."""
        stops = [
            ColorStop(position=1.0, r=0, g=0, b=255),
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=0.5, r=0, g=255, b=0)
        ]

        colors = render_gradient(stops, pixel_count=5)

        # Should still render correctly
        assert len(colors) == 5
        assert colors[0] == (255, 0, 0)  # Red (position 0.0)
        assert colors[4] == (0, 0, 255)  # Blue (position 1.0)

    def test_minimum_stops_error(self):
        """Should raise error with less than 2 stops."""
        stops = [ColorStop(position=0.0, r=255, g=0, b=0)]

        with pytest.raises(ValueError, match="At least 2 color stops required"):
            render_gradient(stops, pixel_count=10)


class TestValidateGradientConfig:
    """Tests for gradient configuration validation."""

    def test_valid_config(self):
        """Should pass validation for valid config."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )

        # Should not raise exception
        validate_gradient_config(config)

    def test_minimum_stops(self):
        """Should reject config with less than 2 stops."""
        # GradientConfig will reject this at creation time (Pydantic validation)
        # So we test the validator with a mock object directly
        mock_config = Mock()
        mock_config.stops = [ColorStop(position=0.0, r=255, g=0, b=0)]

        with pytest.raises(ValueError, match="At least 2 color stops required"):
            validate_gradient_config(mock_config)

    def test_unsorted_positions(self):
        """Should reject unsorted color stops."""
        mock_config = Mock()
        mock_config.stops = [
            ColorStop(position=1.0, r=0, g=0, b=255),
            ColorStop(position=0.0, r=255, g=0, b=0)
        ]

        with pytest.raises(ValueError, match="ascending position order"):
            validate_gradient_config(mock_config)

    def test_duplicate_positions(self):
        """Should reject duplicate positions."""
        mock_config = Mock()
        mock_config.stops = [
            ColorStop(position=0.0, r=255, g=0, b=0),
            ColorStop(position=0.0, r=0, g=255, b=0)
        ]

        with pytest.raises(ValueError, match="Duplicate color stop positions"):
            validate_gradient_config(mock_config)

    def test_valid_multi_stop_gradient(self):
        """Should accept valid multi-stop gradient."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=0.3, r=255, g=255, b=0),
                ColorStop(position=0.7, r=0, g=255, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )

        # Should not raise exception
        validate_gradient_config(config)
