"""
Mathematical helpers for smooth, non-flickering light behavior.
"""

import math


def smoothstep(t: float) -> float:
    """Smooth ease-in / ease-out curve."""
    return t * t * (3 - 2 * t)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


class SmoothNoise:
    """
    Very low-frequency noise generator.

    Used to simulate slow cloud movement without flicker.
    """

    def __init__(self, intensity: float):
        self.intensity = intensity
        self.phase = 0.0

    def step(self, dt: float) -> float:
        # Extremely slow phase evolution
        self.phase += dt * 0.05
        return math.sin(self.phase) * self.intensity

