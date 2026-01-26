"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.common.config import load_database_config, load_redis_config
from src.common.logging import configure_logging
from src.stream_service.infrastructure.postgres_repository import PostgresRepository
from src.stream_service.infrastructure.redis_cache import RedisLatestPriceCache

configure_logging()

# Add project root to Python path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def db_config():
    """Database configuration fixture."""
    return load_database_config()


@pytest.fixture(scope="session")
def redis_config():
    """Redis configuration fixture."""
    return load_redis_config()


@pytest.fixture
def postgres_repo(db_config):
    """PostgreSQL repository fixture."""
    return PostgresRepository(db_config)


@pytest.fixture
def redis_cache(redis_config):
    """Redis cache fixture."""
    return RedisLatestPriceCache(redis_config)


@pytest.fixture
def sample_instrument():
    """Sample instrument for testing."""
    from src.stream_service.domain.models import Instrument

    return Instrument(
        isin="INE123A010",
        instrument_key="NSE_EQ|INE123A010",
        exchange="NSE",
        trading_symbol="TEST",
        instrument_name="Test Instrument",
        metadata={"test": "true"},
    )
