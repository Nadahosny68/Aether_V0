# utils/logger.py

import logging
import os
from datetime import datetime

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR  = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger that writes to both the console and logs/pipeline.log.
    Usage:  log = get_logger("fetch_weather_forecast")
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)

    if logger.handlers:           # already configured — don't add duplicate handlers
        return logger

    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger