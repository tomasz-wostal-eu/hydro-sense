"""
Season-specific color temperature and brightness profiles.
"""

SEASONS = {
    "winter": {
        "sunrise": {"h_start": 10, "h_end": 45, "s_start": 1.0, "s_end": 0.25},
        "sunset":  {"h_start": 45, "h_end": 10, "s_start": 0.25, "s_end": 1.0},
        "max_v": 0.8,
        "cloud_intensity": 0.02,
    },
    "spring": {
        "sunrise": {"h_start": 15, "h_end": 55, "s_start": 1.0, "s_end": 0.2},
        "sunset":  {"h_start": 55, "h_end": 15, "s_start": 0.2, "s_end": 1.0},
        "max_v": 1.0,
        "cloud_intensity": 0.03,
    },
    "summer": {
        "sunrise": {"h_start": 20, "h_end": 60, "s_start": 0.9, "s_end": 0.15},
        "sunset":  {"h_start": 60, "h_end": 20, "s_start": 0.15, "s_end": 0.9},
        "max_v": 1.0,
        "cloud_intensity": 0.04,
    },
    "autumn": {
        "sunrise": {"h_start": 12, "h_end": 50, "s_start": 1.0, "s_end": 0.3},
        "sunset":  {"h_start": 50, "h_end": 12, "s_start": 0.3, "s_end": 1.0},
        "max_v": 0.9,
        "cloud_intensity": 0.03,
    },
}

