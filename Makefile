.PHONY: test test-fast test-coverage test-watch install-dev clean help venv

# Detect Python command (prefer venv if it exists)
VENV_PYTHON := .venv/bin/python
PYTHON := $(shell if [ -f $(VENV_PYTHON) ]; then echo $(VENV_PYTHON); else command -v python3 2> /dev/null || command -v python 2> /dev/null; fi)
PIP := $(PYTHON) -m pip

help:
	@echo "Available targets:"
	@echo "  make venv          - Create virtual environment"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make test          - Run all tests without coverage (fast, ~3 min)"
	@echo "  make test-fast     - Alias for 'make test'"
	@echo "  make test-coverage - Run tests with coverage (WARNING: may hang on report generation)"
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
	@echo "Running tests without coverage (fast mode)..."
	$(PYTHON) -m pytest -q --no-cov

test-fast: test

test-coverage:
	@echo "⚠️  WARNING: Coverage report generation may hang in Python 3.14.x"
	@echo "⚠️  If tests hang after '276 passed', press Ctrl+C and use 'make test' instead"
	@echo ""
	@sleep 2
	timeout 400 $(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=html || \
		(echo "⚠️  Tests timed out during coverage report. Use 'make test' for faster runs." && exit 1)

test-watch:
	$(PYTHON) -m pytest_watch --no-cov

clean:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage .coverage.* coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Clean complete"
