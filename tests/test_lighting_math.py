"""Tests for lighting_math module."""

import pytest
import math
from app.lighting_math import smoothstep, lerp, SmoothNoise


class TestSmoothstep:
    """Tests for smoothstep function."""

    def test_smoothstep_at_zero(self):
        """Should return 0.0 when t=0."""
        assert smoothstep(0.0) == 0.0

    def test_smoothstep_at_one(self):
        """Should return 1.0 when t=1."""
        assert smoothstep(1.0) == 1.0

    def test_smoothstep_at_half(self):
        """Should return 0.5 when t=0.5."""
        result = smoothstep(0.5)
        assert abs(result - 0.5) < 0.01

    def test_smoothstep_is_smooth(self):
        """Should have smooth transitions (non-linear)."""
        # At 0.25, smoothstep should be less than linear (0.25)
        # because of ease-in
        assert smoothstep(0.25) < 0.25

        # At 0.75, smoothstep should be greater than linear (0.75)
        # because of ease-out
        assert smoothstep(0.75) > 0.75

    def test_smoothstep_monotonic(self):
        """Should be monotonically increasing."""
        values = [smoothstep(t / 10) for t in range(11)]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1]


class TestLerp:
    """Tests for linear interpolation."""

    def test_lerp_at_zero(self):
        """Should return a when t=0."""
        assert lerp(10.0, 20.0, 0.0) == 10.0

    def test_lerp_at_one(self):
        """Should return b when t=1."""
        assert lerp(10.0, 20.0, 1.0) == 20.0

    def test_lerp_at_half(self):
        """Should return midpoint when t=0.5."""
        assert lerp(10.0, 20.0, 0.5) == 15.0

    def test_lerp_negative_values(self):
        """Should work with negative values."""
        assert lerp(-10.0, 10.0, 0.5) == 0.0

    def test_lerp_same_values(self):
        """Should return same value when a=b."""
        assert lerp(5.0, 5.0, 0.5) == 5.0

    def test_lerp_beyond_range(self):
        """Should extrapolate when t>1 or t<0."""
        assert lerp(0.0, 10.0, 2.0) == 20.0
        assert lerp(0.0, 10.0, -1.0) == -10.0


class TestSmoothNoise:
    """Tests for SmoothNoise generator."""

    def test_initialization(self):
        """Should initialize with given intensity."""
        noise = SmoothNoise(intensity=0.5)
        assert noise.intensity == 0.5
        assert noise.phase == 0.0

    def test_step_returns_bounded_value(self):
        """Should return value within [-intensity, intensity]."""
        noise = SmoothNoise(intensity=0.3)
        for _ in range(100):
            value = noise.step(0.1)
            assert -0.3 <= value <= 0.3

    def test_step_updates_phase(self):
        """Should update internal phase on each step."""
        noise = SmoothNoise(intensity=0.5)
        initial_phase = noise.phase
        noise.step(1.0)
        assert noise.phase != initial_phase

    def test_step_deterministic(self):
        """Should produce same sequence with same initial conditions."""
        noise1 = SmoothNoise(intensity=0.5)
        noise2 = SmoothNoise(intensity=0.5)

        values1 = [noise1.step(0.1) for _ in range(10)]
        values2 = [noise2.step(0.1) for _ in range(10)]

        assert values1 == values2

    def test_step_smooth_progression(self):
        """Should produce smooth (continuous) values."""
        noise = SmoothNoise(intensity=0.5)

        # Generate sequence
        values = [noise.step(0.01) for _ in range(100)]

        # Check that adjacent values don't differ too much
        max_diff = max(abs(values[i] - values[i-1]) for i in range(1, len(values)))

        # With dt=0.01, adjacent values should be very close
        assert max_diff < 0.1

    def test_zero_intensity(self):
        """Should always return 0 when intensity is 0."""
        noise = SmoothNoise(intensity=0.0)
        for _ in range(10):
            assert noise.step(1.0) == 0.0
