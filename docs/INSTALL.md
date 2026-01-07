# Installation

There are two ways to install HydroSense: with Ansible (recommended) or manually.

## Option 1: Automated Setup with Ansible (Recommended)

The easiest way to set up one or more Raspberry Pi devices:

```bash
# Clone repository on your local machine
git clone <your-repo-url>
cd hydrosense/ansible

# Configure MQTT password (optional)
cp group_vars/raspberry_pi/vault.yml.example group_vars/raspberry_pi/vault.yml
ansible-vault edit group_vars/raspberry_pi/vault.yml

# Test connectivity
make ping

# Run initial setup (installs everything, configures system)
make setup

# Reboot to apply boot configuration
make reboot
```

This will automatically:
- Update system packages
- Install all dependencies (Python, build tools, libraries)
- Enable SPI and 1-Wire interfaces
- Create project directories and virtual environment
- Install Python packages
- Configure and start systemd service

## Option 2: Manual Installation

For manual setup on a Raspberry Pi:

```bash
# Clone repository
git clone <your-repo-url>
cd hydrosense

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Configure environment:**
```bash
cp .env.example .env
nano .env
```

**Install systemd service:**
```bash
sudo cp hydrosense.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hydrosense
sudo systemctl start hydrosense
```
