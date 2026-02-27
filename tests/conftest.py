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
    """
    Provide database configuration for tests.
    
    Returns:
        dict: Database configuration mapping as returned by load_database_config().
    """
    return load_database_config()


@pytest.fixture(scope="session")
def redis_config():
    """
    Provide Redis connection configuration for tests. This fixture is session-scoped and intended for use by test functions that need Redis settings.
    
    Returns:
        mapping: A mapping of Redis configuration values (connection info and options).
    """
    return load_redis_config()


@pytest.fixture
def postgres_repo(db_config):
    """
    Provide a PostgresRepository initialized with the test database configuration.
    
    Parameters:
        db_config: Database configuration returned by the `db_config` fixture.
    
    Returns:
        PostgresRepository: A repository instance initialized with `db_config`.
    """
    return PostgresRepository(db_config)


@pytest.fixture
def redis_cache(redis_config):
    """
    Provides a RedisLatestPriceCache initialized with the test Redis configuration.
    
    Parameters:
        redis_config: Redis configuration object used to initialize the cache.
    
    Returns:
        RedisLatestPriceCache: A cache instance configured with `redis_config`.
    """
    return RedisLatestPriceCache(redis_config)


@pytest.fixture
def sample_instrument():
    """
    Provide a sample Instrument model instance for tests.
    
    Returns:
        Instrument: An Instrument instance with preset fields:
            - isin: "INE123A010"
            - instrument_key: "NSE_EQ|INE123A010"
            - exchange: "NSE"
            - trading_symbol: "TEST"
            - instrument_name: "Test Instrument"
            - metadata: {"test": "true"}
    """
    from src.stream_service.domain.models import Instrument

    return Instrument(
        isin="INE123A010",
        instrument_key="NSE_EQ|INE123A010",
        exchange="NSE",
        trading_symbol="TEST",
        instrument_name="Test Instrument",
        metadata={"test": "true"},
    )
