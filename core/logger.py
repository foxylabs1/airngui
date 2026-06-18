"""
Logging for AirNGUI.
Writes to ~/.local/share/airngui/airngui.log
"""

import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "airngui")
LOG_FILE = os.path.join(LOG_DIR, "airngui.log")
CAPTURE_DIR = os.path.join(os.path.expanduser("~"), "airngui-captures")


def setup_logging():
    """Initialize logging to file and return the logger."""
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(CAPTURE_DIR, exist_ok=True)

    logger = logging.getLogger("airngui")
    logger.setLevel(logging.DEBUG)

    # File handler - all levels
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    # Console handler - warnings and above
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    logger.info("AirNGUI started")
    return logger


def get_logger(name="airngui"):
    """Get a child logger."""
    return logging.getLogger(f"airngui.{name}")


def get_capture_dir():
    """Return the persistent capture directory."""
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    return CAPTURE_DIR
