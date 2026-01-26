"""Redis adapter for the latest-price cache."""

from __future__ import annotations

import json

import redis

from src.common.config import RedisConfig
from src.common.logging import configure_logging
from src.stream_service.domain.models import Tick
from src.stream_service.domain.repositories import LatestPriceCache


class RedisLatestPriceCache(LatestPriceCache):
    """Redis-backed cache storing the most recent price per instrument."""

    def __init__(self, config: RedisConfig) -> None:
        self.config = config
        self.logger = configure_logging(__name__)
        self.client = redis.Redis.from_url(config.url, decode_responses=True)

    def upsert_price(self, tick: Tick) -> None:
        """Store or update the latest price snapshot for ``tick.instrument_id``."""
        payload = json.dumps({"price": tick.price, "ts": tick.timestamp.isoformat()})
        key = f"ltp:{tick.instrument_id}"
        self.client.setex(key, self.config.ttl_seconds, payload)
        self.logger.debug("Cached latest price for %s", key)
