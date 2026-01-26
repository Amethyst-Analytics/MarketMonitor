"""Structured logging utilities used across services."""

import logging
from typing import Optional


def configure_logging(
    name: Optional[str] = None, level: int = logging.INFO
) -> logging.Logger:
    """Configure and return a logger with a consistent format."""

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
