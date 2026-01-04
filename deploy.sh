#!/bin/bash
set -e

# Configuration - Edit these values for your setup
REMOTE_USER="deploy"
REMOTE_HOST="192.168.55.144" # Change to IP address if needed (e.g., 192.168.1.100)
REMOTE_PATH="/home/deploy/hydrosense"
SSH_KEY="${HOME}/.ssh/personal"

echo "================================"
echo "HydroSense Deployment Script"
echo "================================"
echo ""
echo "Target: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
echo ""

# Check if remote host is reachable
echo "Checking connectivity..."
if ! ping -c 1 -W 2 ${REMOTE_HOST} &>/dev/null; then
  echo "WARNING: Cannot ping ${REMOTE_HOST}"
  echo "Proceeding anyway, but deployment may fail if host is unreachable"
fi

# Sync files using rsync
echo ""
echo "Syncing files..."
rsync -avz \
  -e "ssh -i ${SSH_KEY}" \
  --exclude='.venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='.git/' \
  --exclude='.env' \
  --exclude='.DS_Store' \
  --exclude='*.swp' \
  --exclude='*.swo' \
  --delete \
  ./ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/

echo ""
echo "Files synced successfully!"

# Check if systemd service exists and is running
echo ""
echo "Checking for systemd service..."
if ssh -i ${SSH_KEY} ${REMOTE_USER}@${REMOTE_HOST} "systemctl is-active --quiet hydrosense.service" 2>/dev/null; then
  echo "Service is running, restarting..."
  ssh -i ${SSH_KEY} ${REMOTE_USER}@${REMOTE_HOST} "sudo systemctl restart hydrosense.service"
  echo "Service restarted successfully!"

  # Show service status
  echo ""
  echo "Service status:"
  ssh -i ${SSH_KEY} ${REMOTE_USER}@${REMOTE_HOST} "systemctl status hydrosense.service --no-pager -l" || true
elif ssh -i ${SSH_KEY} ${REMOTE_USER}@${REMOTE_HOST} "systemctl is-enabled --quiet hydrosense.service" 2>/dev/null; then
  echo "Service exists but is not running. Start it with:"
  echo "  ssh -i ${SSH_KEY} ${REMOTE_USER}@${REMOTE_HOST} 'sudo systemctl start hydrosense.service'"
else
  echo "No systemd service found (hydrosense.service)"
  echo "To create one, see README.md for service file template"
fi

echo ""
echo "================================"
echo "Deployment complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "  - SSH to Pi: ssh ${REMOTE_USER}@${REMOTE_HOST}"
echo "  - View logs: journalctl -u hydrosense -f"
echo "  - Test API: curl http://${REMOTE_HOST}:8000/docs"
