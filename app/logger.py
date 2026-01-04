"""
Centralized logging configuration for HydroSense.

Logs INFO and DEBUG to stdout, WARNING and ERROR to stderr.
Log level is configurable via LOG_LEVEL environment variable.
"""

import logging
import sys
from app.config import LOG_LEVEL


class LevelFilter(logging.Filter):
    """Filter log records by level range."""

    def __init__(self, level_min: int, level_max: int):
        super().__init__()
        self.level_min = level_min
        self.level_max = level_max

    def filter(self, record: logging.LogRecord) -> bool:
        return self.level_min <= record.levelno <= self.level_max


def setup_logging() -> logging.Logger:
    """
    Configure application-wide logging to stdout/stderr.

    Returns:
        Logger instance for hydrosense
    """
    # Create logger
    logger = logging.getLogger("hydrosense")
    logger.setLevel(LOG_LEVEL)

    # Prevent propagation to root logger
    logger.propagate = False

    # Remove any existing handlers (for reload safety)
    logger.handlers.clear()

    # INFO and DEBUG to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(LevelFilter(logging.DEBUG, logging.INFO))

    # WARNING and ERROR to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    # Format: "2025-01-15 14:30:45 - hydrosense - INFO - Message"
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    return logger


# Global logger instance
logger = setup_logging()
