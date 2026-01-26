"""Tests for Redis cache implementation."""

from __future__ import annotations

import pytest

from src.stream_service.domain.models import Tick
from src.stream_service.infrastructure.redis_cache import RedisLatestPriceCache
from src.common.exceptions import DataIngestionError


class TestRedisLatestPriceCache:
    """Test suite for RedisLatestPriceCache."""

    def test_upsert_price(self, redis_cache, sample_instrument):
        """Test price upsert."""
        tick = Tick(
            timestamp="2025-01-01T12:00:00Z",
            instrument_id=1,
            price=150.25,
        )
        redis_cache.upsert_price(tick)  # Should not raise

    def test_connection_failure(self, monkeypatch):
        """Test graceful handling of Redis connection failure."""
        from src.common.config import RedisConfig

        bad_cfg = RedisConfig(url="redis://invalid:9999", ttl=10)
        cache = RedisLatestPriceCache(bad_cfg)
        tick = Tick(
            timestamp="2025-01-01T12:00:00Z",
            instrument_id=1,
            price=150.25,
        )
        with pytest.raises(DataIngestionError):
            cache.upsert_price(tick)
