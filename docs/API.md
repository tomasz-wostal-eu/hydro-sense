# API Endpoints

Interactive API docs are available at `/docs` (Swagger UI) on your device's IP address.

- **`POST /backlight/rgb`**: Set a solid RGB color.
- **`POST /backlight/hsv`**: Set a solid HSV color.
- **`POST /backlight/off`**: Turn off the LEDs.
- **`POST /backlight/sunrise/auto`**: Start a sunrise animation.
- **`POST /backlight/sunset/auto`**: Start a sunset animation.
- **`POST /backlight/gradient/static`**: Set a static gradient.
- **`POST /backlight/gradient/animated`**: Start an animated gradient.
- **`GET /backlight/gradient/presets`**: List available gradient presets.
- **`GET /backlight/gradient/preset/{name}`**: Apply a gradient preset.
- **`POST /backlight/gradient/preset/save`**: Save a new gradient preset.
- **`DELETE /backlight/gradient/preset/{name}`**: Delete a gradient preset.
- **`GET /backlight/state`**: Get the current state of the LEDs.
- **`GET /temperature`**: Get readings from all temperature sensors.
- **`GET /temperature/{sensor_id}`**: Get a reading from a specific temperature sensor.
- **`GET /relay`**: Get status of all relays.
- **`POST /relay/{relay_id}/on`**: Turn on a relay.
- **`POST /relay/{relay_id}/off`**: Turn off a relay.
- **`GET /water-level`**: Get current water level sensor status.
- **`GET /pump-automation`**: Get pump automation status.
- **`POST /pump-automation/mode`**: Set pump automation mode (AUTO/MANUAL/DISABLED).
