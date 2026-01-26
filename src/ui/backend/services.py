"""Service layer for the UI backend."""

from __future__ import annotations

import os
from typing import List

from src.common.config import load_database_config, load_redis_config
from src.common.logging import configure_logging
from src.common.exceptions import ValidationError, ExternalServiceError
from src.stream_service.domain.models import Instrument, Tick
from src.stream_service.infrastructure.postgres_repository import PostgresRepository
from src.stream_service.infrastructure.redis_cache import RedisLatestPriceCache

logger = configure_logging(__name__)

__all__ = [
    "get_auth_status",
    "list_subscribed_instruments",
    "get_latest_prices",
    "get_tick_history",
]


def get_auth_status() -> dict:
    """Return whether an access token is configured."""
    token = os.getenv("UPSTOX_ACCESS_TOKEN")
    return {"has_token": bool(token)}


def list_subscribed_instruments() -> List[dict]:
    """Return instruments with tracking_status=true."""
    # Placeholder: query DB once tracking_status column exists
    logger.info("Fetching subscribed instruments (placeholder)")
    return []


def get_latest_prices(isins: List[str]) -> dict:
    """Fetch latest prices from Redis for given ISINs."""
    if not isins:
        raise ValidationError("ISIN list cannot be empty")
    logger.info("Fetching latest prices for %d ISINs", len(isins))
    cfg = load_redis_config()
    cache = RedisLatestPriceCache(cfg)
    result = {}
    for isin in isins:
        # Map ISIN → instrument_id first (placeholder)
        # For now return empty
        result[isin] = None
    return result


def get_tick_history(isin: str, start: str, end: str) -> List[dict]:
    """Return historical ticks for an ISIN between timestamps."""
    if not isin:
        raise ValidationError("ISIN is required")
    if not start or not end:
        raise ValidationError("Start and end timestamps are required")
    logger.info("Fetching tick history for ISIN=%s from %s to %s", isin, start, end)
    # Placeholder: query TimescaleDB
    return []
