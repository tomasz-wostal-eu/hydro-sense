"""
Astronomical sunrise/sunset calculation using Astral.
"""

from astral import LocationInfo
from astral.sun import sun
from datetime import datetime, timezone


def get_sun_times(latitude: float, longitude: float):
    location = LocationInfo(latitude=latitude, longitude=longitude)
    today = datetime.now(timezone.utc)
    s = sun(location.observer, date=today)
    return s["sunrise"], s["sunset"]

