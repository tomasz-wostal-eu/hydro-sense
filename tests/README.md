# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the LED API project, including unit tests, integration tests, and API tests. All tests use mocked hardware to run on any platform without requiring a Raspberry Pi.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared pytest fixtures
├── test_lighting_math.py       # Math utility tests
├── test_state.py              # State management tests
├── test_gradient.py           # Gradient rendering tests
├── test_config.py             # Configuration tests
├── test_led.py                # LED hardware abstraction tests
├── test_animations.py         # Animation tests
├── test_gradient_presets.py   # Preset management tests
└── test_api.py                # FastAPI endpoint tests
```

## Test Coverage

### Unit Tests

**test_lighting_math.py**
- `smoothstep()` - Smooth easing function
- `lerp()` - Linear interpolation
- `SmoothNoise` - Cloud simulation noise generator

**test_state.py**
- LEDState initialization and updates
- Thread-safe state management
- MQTT payload conversion
- State snapshots

**test_gradient.py**
- ColorStop validation
- GradientConfig validation
- Gradient rendering algorithm
- Multi-color interpolation
- Offset and animation support

**test_config.py**
- Default configuration values
- Environment variable overrides
- Type conversions

### Integration Tests

**test_led.py** (with hardware mocks)
- LED strip initialization
- Brightness control
- RGB color control
- HSV color control
- Pixel array operations
- Thread safety
- Animation lock

**test_animations.py** (with hardware mocks)
- Cloudy sunrise animation
- Cloudy sunset animation
- Cancellation support
- Season profiles
- Error handling
- Concurrent animation blocking

**test_gradient_presets.py** (with file I/O mocks)
- Preset creation and validation
- Default presets
- Loading presets from file
- Saving presets to file
- Retrieving presets
- Deleting presets
- Listing preset names

### API Tests

**test_api.py** (with TestClient)
- Health check endpoint
- RGB color endpoint
- HSV color endpoint
- Brightness endpoint
- Turn off endpoint
- Gradient endpoints (static and animated)
- State query endpoint
- Preset endpoints
- Animation endpoints (sunrise/sunset)
- Error handling

## Running Tests

### Prerequisites

```bash
# Install development dependencies
pip install -r requirements-dev.txt
```

### Quick Start (Recommended)

```bash
# Run all tests (fast mode, no coverage, ~3 minutes) ✅
make test
# or
pytest -q --no-cov
```

**All 276 tests pass in ~2:30-3:00 minutes**

### Basic Usage

```bash
# Run all tests (fast mode)
pytest -q --no-cov

# Run all tests with verbose output
pytest -v --no-cov

# Run specific test file
pytest tests/test_gradient.py -v --no-cov

# Run specific test class
pytest tests/test_api.py::TestRGBEndpoint -v --no-cov

# Run specific test
pytest tests/test_api.py::TestRGBEndpoint::test_set_rgb_valid -v --no-cov
```

### Coverage Reports (⚠️ Known Issues)

```bash
# Run tests with coverage (may hang on Python 3.14+)
pytest --cov=app

# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open coverage report in browser
open htmlcov/index.html
```

**⚠️ WARNING:** Coverage report generation may hang on Python 3.14+ after all tests complete (276 passed). If tests hang:
1. Press `Ctrl+C` to interrupt
2. Use `--no-cov` flag instead (fast, no hanging)
3. See "Known Issues" section below

### Using Makefile

```bash
# Run all tests (fast, recommended)
make test

# Run with coverage (may hang)
make test-coverage

# Clean test artifacts
make clean
```

## Known Issues

### Coverage Reporting Hangs (Python 3.14.2)

**Symptom:** All 276 tests complete successfully but the process hangs at 100% CPU during coverage report generation.

**Root Cause:** Bug in pytest-cov 7.4.3 or coverage.py 4.1.0 with Python 3.14.2

**Workaround:**

```bash
# ✅ Fast mode (no coverage, no hanging)
pytest -q --no-cov       # ~2:30-3:00 minutes
make test                # Uses --no-cov automatically

# ⚠️ May hang after tests complete
pytest                   # Default includes coverage
make test-coverage       # Includes timeout but still may hang
```

**CI/CD Solution:**
- GitHub Actions runs tests twice:
  1. Fast mode without coverage (primary validation)
  2. With coverage + timeout (optional, non-fatal if it times out)

## Hardware Mocking

All tests that interact with Raspberry Pi hardware use mocks:

**conftest.py** provides:
- `mock_rpi_hardware` - Auto-fixture that mocks `rpi_ws281x` library
- `mock_mqtt` - MQTT client mock
- `disable_mqtt` - Disable MQTT for specific tests
- `disable_temperature` - Disable temperature sensors for specific tests

Tests can run on:
- macOS
- Linux (x86_64, ARM)
- Windows
- CI/CD pipelines (GitHub Actions, GitLab CI, etc.)

## Writing New Tests

### Basic Test Structure

```python
import pytest
from app.your_module import your_function

class TestYourFeature:
    """Tests for your feature."""

    def test_basic_functionality(self):
        """Should do something specific."""
        result = your_function()
        assert result == expected_value

    def test_edge_case(self):
        """Should handle edge case."""
        with pytest.raises(ValueError):
            your_function(invalid_input)
```

### Using Fixtures

```python
@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

def test_with_fixture(sample_data):
    """Test using fixture."""
    assert sample_data["key"] == "value"
```

### Testing Async Functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Mocking Hardware

```python
from unittest.mock import Mock, patch

def test_led_function():
    """Test with mocked LED hardware."""
    with patch('app.led.PixelStrip') as mock_strip:
        # Configure mock
        mock_strip.return_value.numPixels.return_value = 30

        # Run test
        from app.led import LedStrip
        strip = LedStrip(count=30)

        # Verify
        assert strip.count == 30
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Test Best Practices

1. **One assertion per test** (when possible) - Makes failures clearer
2. **Descriptive test names** - Should explain what is being tested
3. **Use fixtures for setup** - Avoid code duplication
4. **Mock external dependencies** - Tests should be isolated
5. **Test edge cases** - Not just happy paths
6. **Keep tests fast** - Use mocks, avoid network/disk I/O
7. **Test thread safety** - For concurrent code

## Troubleshooting

### Tests fail with "ModuleNotFoundError"

Ensure you're running tests from the project root:
```bash
cd /path/to/hydrosense
pytest
```

### Tests fail with "rpi_ws281x not found"

The auto-fixture in `conftest.py` should handle this. Check that `conftest.py` is in the `tests/` directory.

### Coverage not showing all files

Make sure you're running from project root and using:
```bash
pytest --cov=app
```

### Slow tests

Check for actual I/O operations or network calls. All hardware and external dependencies should be mocked.

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure coverage remains high (>80%)
3. Run full test suite before committing
4. Update this documentation if needed
