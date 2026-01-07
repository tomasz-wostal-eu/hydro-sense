.PHONY: help setup deploy status reboot ping test create-user tailscale tailscale-auth

help:
	@echo "HydroSense Ansible Commands"
	@echo ""
	@echo "  make ping           - Test connectivity to all Raspberry Pi hosts"
	@echo "  make create-user    - Create deploy user with sudo and SSH key (run first!)"
	@echo "  make setup          - Initial setup of Raspberry Pi (run once)"
	@echo "  make tailscale      - Install Tailscale (requires auth key in vault OR manual auth)"
	@echo "  make tailscale-auth - Manually authenticate Tailscale (interactive)"
	@echo "  make deploy         - Deploy application to Raspberry Pi"
	@echo "  make status         - Check service status and logs"
	@echo "  make reboot         - Reboot Raspberry Pi devices"
	@echo "  make test           - Run connectivity and basic checks"
	@echo ""
	@echo "Target specific hosts:"
	@echo "  make deploy HOST=led-stripe"
	@echo "  make status HOST=rpi3-rnd-01"
	@echo "  make tailscale HOST=led-stripe"
	@echo ""
	@echo "Initial setup workflow:"
	@echo "  1. make create-user  (creates deploy user, use ansible_user=twostal)"
	@echo "  2. make setup        (configures system, uses ansible_user=deploy)"
	@echo "  3. make tailscale    (optional: install Tailscale - needs auth key in vault)"
	@echo "  4. make deploy       (deploys application)"
	@echo ""
	@echo "Tailscale setup (choose one):"
	@echo "  Option A - Manual auth (recommended for single setup):"
	@echo "    1. make tailscale        (installs Tailscale)"
	@echo "    2. make tailscale-auth   (interactive authentication)"
	@echo ""
	@echo "  Option B - Automated with auth key:"
	@echo "    1. Get key: https://login.tailscale.com/admin/settings/keys"
	@echo "    2. ansible-vault edit group_vars/raspberry_pi/vault.yml"
	@echo "    3. make tailscale        (auto-authenticates)"

ping:
	ansible raspberry_pi -m ping

create-user:
ifdef HOST
	ansible-playbook playbooks/create-deploy-user.yml --limit $(HOST) -e ansible_user=twostal
else
	ansible-playbook playbooks/create-deploy-user.yml -e ansible_user=twostal
endif

tailscale:
ifdef HOST
	ansible-playbook playbooks/tailscale-setup.yml --limit $(HOST)
else
	ansible-playbook playbooks/tailscale-setup.yml
endif

tailscale-auth:
ifdef HOST
	ansible-playbook playbooks/tailscale-auth-manual.yml --limit $(HOST)
else
	ansible-playbook playbooks/tailscale-auth-manual.yml
endif

setup:
ifdef HOST
	ansible-playbook playbooks/setup.yml --limit $(HOST) -vv
else
	ansible-playbook playbooks/setup.yml -vv
endif

deploy:
ifdef HOST
	ansible-playbook playbooks/deploy.yml --limit $(HOST) -vv
else
	ansible-playbook playbooks/deploy.yml -vv
endif

status:
ifdef HOST
	ansible-playbook playbooks/status.yml --limit $(HOST) -vv
else
	ansible-playbook playbooks/status.yml -vv
endif

reboot:
ifdef HOST
	ansible-playbook playbooks/reboot.yml --limit $(HOST)
else
	ansible-playbook playbooks/reboot.yml
endif

test:
	@echo "Testing SSH connectivity..."
	ansible raspberry_pi -m ping
	@echo ""
	@echo "Checking system uptime..."
	ansible raspberry_pi -a "uptime"
	@echo ""
	@echo "Checking HydroSense service..."
	ansible raspberry_pi -b -m systemd -a "name=hydrosense" || true
