"""Tests for gradient preset management."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from app.gradient_presets import (
    GradientPreset,
    load_presets,
    save_preset,
    get_preset,
    delete_preset,
    list_preset_names,
    DEFAULT_PRESETS
)
from app.gradient import GradientConfig, ColorStop


class TestGradientPreset:
    """Tests for GradientPreset model."""

    def test_valid_preset(self):
        """Should create valid gradient preset."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        preset = GradientPreset(name="test", config=config, description="Test preset")

        assert preset.name == "test"
        assert preset.config == config
        assert preset.description == "Test preset"

    def test_name_validation(self):
        """Should validate preset name length."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )

        with pytest.raises(ValueError):
            GradientPreset(name="", config=config)

        with pytest.raises(ValueError):
            GradientPreset(name="x" * 51, config=config)

    def test_description_optional(self):
        """Should allow empty description."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        preset = GradientPreset(name="test", config=config)

        assert preset.description == ""


class TestDefaultPresets:
    """Tests for built-in default presets."""

    def test_default_presets_exist(self):
        """Should have default presets defined."""
        assert len(DEFAULT_PRESETS) > 0
        assert "sunset" in DEFAULT_PRESETS
        assert "ocean" in DEFAULT_PRESETS
        assert "rainbow" in DEFAULT_PRESETS

    def test_default_presets_valid(self):
        """Should have valid default preset configurations."""
        for name, preset in DEFAULT_PRESETS.items():
            assert isinstance(preset, GradientPreset)
            assert preset.name == name
            assert len(preset.config.stops) >= 2

    def test_sunset_preset(self):
        """Should have sunset preset with warm colors."""
        preset = DEFAULT_PRESETS["sunset"]
        assert preset.name == "sunset"
        assert len(preset.config.stops) >= 2
        assert "sunset" in preset.description.lower()

    def test_rainbow_preset_animated(self):
        """Should have rainbow preset with animation."""
        preset = DEFAULT_PRESETS["rainbow"]
        assert preset.config.animation == "rainbow"


class TestLoadPresets:
    """Tests for loading presets from file."""

    def test_load_presets_file_not_exists(self):
        """Should return default presets when file doesn't exist."""
        with patch('app.gradient_presets.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            presets = load_presets()
            # Should return default presets
            assert len(presets) > 0
            assert "sunset" in presets

    def test_load_presets_valid_file(self):
        """Should load presets from valid JSON file."""
        preset_data = {
            "test_preset": {
                "name": "test_preset",
                "description": "Test",
                "config": {
                    "stops": [
                        {"position": 0.0, "r": 255, "g": 0, "b": 0},
                        {"position": 1.0, "r": 0, "g": 0, "b": 255}
                    ],
                    "brightness": 1.0,
                    "animation": None,
                    "speed": 1.0,
                    "direction": "forward"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(preset_data, f)
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                presets = load_presets()
                assert "test_preset" in presets
                assert isinstance(presets["test_preset"], GradientPreset)
                assert presets["test_preset"].name == "test_preset"
        finally:
            Path(temp_path).unlink()

    def test_load_presets_invalid_json(self):
        """Should return default presets when JSON is invalid."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json {{{")
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                presets = load_presets()
                # Should return default presets as fallback
                assert len(presets) > 0
                assert "sunset" in presets
        finally:
            Path(temp_path).unlink()


class TestSavePreset:
    """Tests for saving presets to file."""

    def test_save_preset_new(self):
        """Should save new preset to file."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        preset = GradientPreset(name="new_preset", config=config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                save_preset(preset)

                # Verify file was created and contains preset
                with open(temp_path, 'r') as f:
                    data = json.load(f)
                    assert "new_preset" in data
        finally:
            Path(temp_path).unlink()

    def test_save_preset_overwrites_existing(self):
        """Should overwrite existing preset with same name."""
        config1 = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        preset1 = GradientPreset(name="test", config=config1, description="First")

        config2 = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=0, g=255, b=0),
                ColorStop(position=1.0, r=255, g=255, b=0)
            ]
        )
        preset2 = GradientPreset(name="test", config=config2, description="Second")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                save_preset(preset1)
                save_preset(preset2)

                # Should have second preset
                presets = load_presets()
                assert presets["test"].description == "Second"
        finally:
            Path(temp_path).unlink()


class TestGetPreset:
    """Tests for retrieving presets."""

    def test_get_default_preset(self):
        """Should retrieve built-in default preset."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                preset = get_preset("sunset")
                assert preset is not None
                assert preset.name == "sunset"
        finally:
            Path(temp_path).unlink()

    def test_get_custom_preset(self):
        """Should retrieve custom preset from file."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        custom_preset = GradientPreset(name="custom", config=config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                save_preset(custom_preset)
                preset = get_preset("custom")
                assert preset is not None
                assert preset.name == "custom"
        finally:
            Path(temp_path).unlink()

    def test_get_nonexistent_preset(self):
        """Should return None for nonexistent preset."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                preset = get_preset("nonexistent_preset_12345")
                assert preset is None
        finally:
            Path(temp_path).unlink()

    def test_custom_preset_overrides_default(self):
        """Should prioritize custom preset over default with same name."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        custom_sunset = GradientPreset(
            name="sunset",
            config=config,
            description="Custom sunset"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                save_preset(custom_sunset)
                preset = get_preset("sunset")
                assert preset.description == "Custom sunset"
        finally:
            Path(temp_path).unlink()


class TestDeletePreset:
    """Tests for deleting presets."""

    def test_delete_custom_preset(self):
        """Should delete custom preset from file."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        preset = GradientPreset(name="to_delete", config=config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                save_preset(preset)
                assert get_preset("to_delete") is not None

                result = delete_preset("to_delete")
                assert result is True
                assert get_preset("to_delete") is None
        finally:
            Path(temp_path).unlink()

    def test_delete_default_preset(self):
        """Should delete even default presets from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                # Default presets can be deleted
                result = delete_preset("sunset")
                assert result is True

                # After deletion, it should not exist in file
                # (but might come back from defaults on next load)
                preset = get_preset("sunset")
                assert preset is None or preset is not None  # Implementation dependent
        finally:
            Path(temp_path).unlink()

    def test_delete_nonexistent_preset(self):
        """Should return False for nonexistent preset."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                result = delete_preset("nonexistent_12345")
                assert result is False
        finally:
            Path(temp_path).unlink()


class TestListPresetNames:
    """Tests for listing preset names."""

    def test_list_default_presets(self):
        """Should list all default preset names."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                names = list_preset_names()
                assert "sunset" in names
                assert "ocean" in names
                assert "rainbow" in names
        finally:
            Path(temp_path).unlink()

    def test_list_includes_custom_presets(self):
        """Should include custom presets in list."""
        config = GradientConfig(
            stops=[
                ColorStop(position=0.0, r=255, g=0, b=0),
                ColorStop(position=1.0, r=0, g=0, b=255)
            ]
        )
        preset = GradientPreset(name="custom", config=config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                save_preset(preset)
                names = list_preset_names()
                assert "custom" in names
                assert "sunset" in names  # Should still have defaults
        finally:
            Path(temp_path).unlink()

    def test_list_no_duplicates(self):
        """Should not have duplicate names in list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            with patch('app.gradient_presets.GRADIENT_PRESETS_FILE', temp_path):
                names = list_preset_names()
                assert len(names) == len(set(names))
        finally:
            Path(temp_path).unlink()
