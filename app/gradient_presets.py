"""
Gradient preset storage and management.

Presets are stored as JSON file for persistence across restarts.
Includes built-in default presets for common use cases.
"""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from app.gradient import GradientConfig, ColorStop
from app.config import GRADIENT_PRESETS_FILE
from app.logger import logger


class GradientPreset(BaseModel):
    """Saved gradient preset with metadata."""
    name: str = Field(..., min_length=1, max_length=50, description="Preset name")
    config: GradientConfig
    description: str = Field("", max_length=200, description="Optional description")


# ============================================================================
# Default Presets
# ============================================================================

DEFAULT_PRESETS = {
    "sunset": GradientPreset(
        name="sunset",
        description="Warm sunset colors from orange to deep purple",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=94, b=77),    # Coral
                ColorStop(position=0.3, r=255, g=140, b=0),    # Dark orange
                ColorStop(position=0.6, r=255, g=69, b=0),     # Orange red
                ColorStop(position=1.0, r=75, g=0, b=130),     # Indigo
            ],
            brightness=0.9,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "ocean": GradientPreset(
        name="ocean",
        description="Deep ocean blues and teals",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=0, g=105, b=148),    # Deep blue
                ColorStop(position=0.5, r=0, g=191, b=255),    # Deep sky blue
                ColorStop(position=1.0, r=64, g=224, b=208),   # Turquoise
            ],
            brightness=0.8,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "rainbow": GradientPreset(
        name="rainbow",
        description="Full spectrum rainbow (animated)",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),      # Red
                ColorStop(position=0.2, r=255, g=165, b=0),    # Orange
                ColorStop(position=0.4, r=255, g=255, b=0),    # Yellow
                ColorStop(position=0.6, r=0, g=255, b=0),      # Green
                ColorStop(position=0.8, r=0, g=0, b=255),      # Blue
                ColorStop(position=1.0, r=138, g=43, b=226),   # Violet
            ],
            brightness=1.0,
            animation="rainbow",
            speed=1.0,
            direction="forward"
        )
    ),

    "fire": GradientPreset(
        name="fire",
        description="Hot fire colors from yellow to deep red",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=255, b=0),    # Yellow
                ColorStop(position=0.4, r=255, g=140, b=0),    # Dark orange
                ColorStop(position=0.7, r=255, g=69, b=0),     # Orange red
                ColorStop(position=1.0, r=139, g=0, b=0),      # Dark red
            ],
            brightness=0.95,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "forest": GradientPreset(
        name="forest",
        description="Natural forest greens",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=34, g=139, b=34),    # Forest green
                ColorStop(position=0.5, r=0, g=128, b=0),      # Green
                ColorStop(position=1.0, r=107, g=142, b=35),   # Olive drab
            ],
            brightness=0.85,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "aurora": GradientPreset(
        name="aurora",
        description="Northern lights effect (animated pulse)",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=0, g=255, b=127),    # Spring green
                ColorStop(position=0.5, r=138, g=43, b=226),   # Blue violet
                ColorStop(position=1.0, r=0, g=191, b=255),    # Deep sky blue
            ],
            brightness=0.9,
            animation="pulse",
            speed=0.8,
            direction="forward"
        )
    ),

    # ========================================================================
    # Aquarium Biotope Presets
    # ========================================================================

    "amazonian": GradientPreset(
        name="amazonian",
        description="Amazon river - warm amber and brown tones for blackwater biotope",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=139, g=90, b=43),    # Saddle brown
                ColorStop(position=0.4, r=184, g=134, b=11),   # Dark goldenrod
                ColorStop(position=0.7, r=205, g=133, b=63),   # Peru
                ColorStop(position=1.0, r=160, g=82, b=45),    # Sienna
            ],
            brightness=0.7,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "asian_river": GradientPreset(
        name="asian_river",
        description="Asian river - green and jade tones for planted biotope",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=0, g=100, b=0),      # Dark green
                ColorStop(position=0.3, r=46, g=139, b=87),    # Sea green
                ColorStop(position=0.7, r=60, g=179, b=113),   # Medium sea green
                ColorStop(position=1.0, r=34, g=139, b=34),    # Forest green
            ],
            brightness=0.75,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "african_lake": GradientPreset(
        name="african_lake",
        description="African Lake - bright blues and yellows for cichlid biotope",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=30, g=144, b=255),   # Dodger blue
                ColorStop(position=0.3, r=0, g=191, b=255),    # Deep sky blue
                ColorStop(position=0.6, r=255, g=215, b=0),    # Gold
                ColorStop(position=1.0, r=255, g=140, b=0),    # Dark orange
            ],
            brightness=0.85,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "reef": GradientPreset(
        name="reef",
        description="Reef aquarium - blue and purple coral colors for marine biotope",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=65, g=105, b=225),   # Royal blue
                ColorStop(position=0.4, r=138, g=43, b=226),   # Blue violet
                ColorStop(position=0.7, r=147, g=112, b=219),  # Medium purple
                ColorStop(position=1.0, r=0, g=206, b=209),    # Dark turquoise
            ],
            brightness=0.8,
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),

    "moonlight": GradientPreset(
        name="moonlight",
        description="Night mode - soft moonlight with deep blue and purple tones",
        config=GradientConfig(
            stops=[
                ColorStop(position=0.0, r=25, g=25, b=112),    # Midnight blue
                ColorStop(position=0.3, r=65, g=105, b=225),   # Royal blue
                ColorStop(position=0.6, r=123, g=104, b=238),  # Medium slate blue
                ColorStop(position=1.0, r=72, g=61, b=139),    # Dark slate blue
            ],
            brightness=0.15,  # Default 15% for full moon
            animation=None,
            speed=1.0,
            direction="forward"
        )
    ),
}


# ============================================================================
# Storage Functions
# ============================================================================

def get_presets_path() -> Path:
    """Get path to presets file, create directory if needed."""
    path = Path(GRADIENT_PRESETS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_presets() -> dict[str, GradientPreset]:
    """
    Load presets from JSON file.

    Returns:
        dict: Preset name -> GradientPreset object

    If file doesn't exist, returns default presets and creates the file.
    """
    path = get_presets_path()

    if not path.exists():
        logger.info(f"Presets file not found, creating with defaults: {path}")
        save_all_presets(DEFAULT_PRESETS)
        return DEFAULT_PRESETS.copy()

    try:
        with open(path, 'r') as f:
            data = json.load(f)

        presets = {}
        for name, preset_data in data.items():
            try:
                presets[name] = GradientPreset(**preset_data)
            except Exception as e:
                logger.warning(f"Failed to load preset '{name}': {e}")
                continue

        logger.info(f"Loaded {len(presets)} gradient presets from {path}")
        return presets

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in presets file: {e}")
        return DEFAULT_PRESETS.copy()
    except Exception as e:
        logger.error(f"Failed to load presets: {e}", exc_info=True)
        return DEFAULT_PRESETS.copy()


def save_preset(preset: GradientPreset) -> None:
    """
    Save single preset (append/update).

    Args:
        preset: GradientPreset to save

    Raises:
        ValueError: If preset name is invalid
    """
    if not preset.name or len(preset.name) > 50:
        raise ValueError("Preset name must be 1-50 characters")

    # Sanitize name (prevent path traversal)
    if '/' in preset.name or '\\' in preset.name or '..' in preset.name:
        raise ValueError("Invalid preset name (contains path separators)")

    presets = load_presets()
    presets[preset.name] = preset
    save_all_presets(presets)

    logger.info(f"Saved gradient preset: {preset.name}")


def save_all_presets(presets: dict[str, GradientPreset]) -> None:
    """
    Save all presets to JSON file.

    Args:
        presets: dict of preset name -> GradientPreset
    """
    path = get_presets_path()

    try:
        data = {name: preset.dict() for name, preset in presets.items()}

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(presets)} presets to {path}")

    except Exception as e:
        logger.error(f"Failed to save presets: {e}", exc_info=True)
        raise


def get_preset(name: str) -> Optional[GradientPreset]:
    """
    Get single preset by name.

    Args:
        name: Preset name

    Returns:
        GradientPreset if found, None otherwise
    """
    presets = load_presets()
    return presets.get(name)


def delete_preset(name: str) -> bool:
    """
    Delete preset by name.

    Args:
        name: Preset name

    Returns:
        True if deleted, False if not found
    """
    presets = load_presets()

    if name not in presets:
        return False

    del presets[name]
    save_all_presets(presets)

    logger.info(f"Deleted gradient preset: {name}")
    return True


def list_preset_names() -> list[str]:
    """
    Get list of all preset names.

    Returns:
        List of preset names sorted alphabetically
    """
    presets = load_presets()
    return sorted(presets.keys())
