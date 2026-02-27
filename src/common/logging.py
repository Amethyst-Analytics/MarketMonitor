"""Structured logging utilities used across services."""

import logging
from typing import Optional


def configure_logging(
    name: Optional[str] = None, level: int = logging.INFO
) -> logging.Logger:
    """
    Configure and return a logger with a consistent, human-readable format.
    
    Parameters:
        name (Optional[str]): Name of the logger; use `None` for the root logger.
        level (int): Logging level to apply to the logger (e.g., `logging.INFO`).
    
    Description:
        If the logger has no handlers, a StreamHandler is added with the format
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s".
    
    Returns:
        logging.Logger: The configured logger instance.
    """

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
