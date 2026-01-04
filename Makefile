.PHONY: test test-coverage test-watch install-dev clean help venv

# Detect Python command
PYTHON := $(shell command -v python3 2> /dev/null || command -v python 2> /dev/null)
PIP := $(PYTHON) -m pip

help:
	@echo "Available targets:"
	@echo "  make venv          - Create virtual environment"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make test          - Run all tests"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo "  make test-watch    - Run tests in watch mode"
	@echo "  make clean         - Remove test artifacts"

venv:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv .venv; \
		echo "Virtual environment created. Activate with: source .venv/bin/activate"; \
	else \
		echo "Virtual environment already exists."; \
	fi

install-dev:
	@if [ -z "$(PYTHON)" ]; then \
		echo "Error: Python not found. Please install Python 3."; \
		exit 1; \
	fi
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest

test-coverage:
	$(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=html

test-watch:
	$(PYTHON) -m pytest_watch

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
