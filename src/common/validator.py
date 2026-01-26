"""Runtime configuration validator."""

from __future__ import annotations

import os
from typing import List

from .config import (
    load_database_config,
    load_redis_config,
    load_stream_config,
    load_upstox_config,
)
from .exceptions import ConfigurationError
from .logging import configure_logging

logger = configure_logging(__name__)

__all__ = ["validate_required_env_vars", "validate_configs", "main"]


def validate_required_env_vars() -> None:
    """Validate that all required environment variables are present."""
    required_vars: List[str] = [
        "UPSTOX_CLIENT_ID",
        "UPSTOX_CLIENT_SECRET",
        "UPSTOX_ACCESS_TOKEN",
        "UPSTOX_PG_DSN",
        "UPSTOX_REDIS_URL",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


def validate_configs() -> None:
    """Validate that configuration objects can be loaded and are coherent."""
    try:
        load_upstox_config()
        load_database_config()
        load_redis_config()
        load_stream_config()
    except Exception as exc:
        raise ConfigurationError(f"Configuration validation failed: {exc}") from exc


def main() -> None:
    """CLI entrypoint for configuration validation."""
    try:
        validate_required_env_vars()
        validate_configs()
        logger.info("Configuration validation passed.")
    except ConfigurationError as exc:
        logger.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
