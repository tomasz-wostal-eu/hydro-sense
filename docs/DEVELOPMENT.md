# Development

## Running Locally

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with auto-reload (development)
sudo -E $(which python) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload
```

## Architecture

The application's main components are in the `app/` directory. `main.py` is the FastAPI entry point, `led.py` handles hardware control, `mqtt_client.py` manages Home Assistant integration, and `animations.py` and `gradient.py` contain the lighting logic.

## Testing

The project includes a comprehensive test suite covering all major components:

**Test Coverage:**
- **Unit Tests**: Core logic (state management, gradient rendering, color math)
- **Integration Tests**: API endpoints, animations, MQTT integration
- **Hardware Mocking**: Tests run on any platform without Raspberry Pi hardware

**Running Tests:**

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
make test
# or
pytest

# Run with coverage report
make test-coverage

# Run specific test file
pytest tests/test_gradient.py

# Run specific test
pytest tests/test_api.py::TestRGBEndpoint::test_set_rgb_valid
```

**Test Files:**
- `test_lighting_math.py` - Mathematical helpers (smoothstep, lerp, noise)
- `test_state.py` - LED state management and thread safety
- `test_gradient.py` - Gradient rendering and validation
- `test_config.py` - Configuration loading and environment variables
- `test_led.py` - LED hardware abstraction (with mocks)
- `test_animations.py` - Sunrise/sunset animations (with mocks)
- `test_gradient_presets.py` - Preset storage and management
- `test_api.py` - FastAPI endpoints (with TestClient)

**Coverage Report:**

After running `make test-coverage`, open `htmlcov/index.html` in your browser to see detailed coverage information.

**CI/CD Integration:**

Tests can be integrated into CI/CD pipelines. All tests use mocked hardware and run without physical Raspberry Pi.

## Tailscale

For secure remote access, Tailscale can be set up using Ansible. You can use a reusable auth key stored in the Ansible vault for automatic setup, or authenticate manually.
