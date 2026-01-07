# Troubleshooting

- **Service won't start**: Check `journalctl -u hydrosense` for errors. Permission errors often relate to GPIO/DMA access. The systemd service must run as root.
- **MQTT not connecting**: Verify broker, port, and credentials in your `.env` file. Use `mosquitto_sub` to test the connection.
- **LEDs not appearing in Home Assistant**: Ensure MQTT is enabled and the integration is set up in HA. Check for discovery messages on the `homeassistant/light/.../config` topic.
- **Water level sensor always shows OK:**
- Check wiring: Sensor wire 2 must connect to GND, not VCC
- Verify pull-up resistor is configured in code (default)
- Test GPIO directly: `sudo python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP); print(GPIO.input(23)); GPIO.cleanup()"`
- **Water level sensor always shows LOW:**
- Sensor wires might be shorted
- Check for water/moisture on sensor contacts
- Verify sensor is actually above water level
- **Relay not clicking:**
- Check relay module power (VCC/GND)
- Verify GPIO pin number in configuration
- Test GPIO directly with a Python script
- Check `active_low` setting matches your relay module
- Ensure service runs as root: `systemctl status hydrosense`
- **Pump runs continuously:**
- Check if pump automation is in DISABLED mode
- Verify auto-shutoff timer is enabled (`max_on_time > 0`)
- Check logs: `sudo journalctl -u hydrosense -f`
- **Troubleshooting HA Integration**
- **Devices not appearing:**
1. Check MQTT integration is connected
2. Verify `.env` has correct broker IP
3. Check logs: `sudo journalctl -u hydrosense -f`
4. Restart: `sudo systemctl restart hydrosense`

- **Temperature sensors not updating:**
1. Check sensor detection: `ls /sys/bus/w1/devices/`
2. Should see sensors starting with `28-`
3. Test API: `curl http://rpizero-01:8000/temperature`

- **MQTT commands not working:**
1. Verify `MQTT_CLIENT_ID` matches in commands
2. Validate JSON payload
3. Monitor MQTT: `mosquitto_sub -h <broker> -t 'hydrosense/#' -v`
