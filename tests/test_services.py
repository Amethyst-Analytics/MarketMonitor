"""Tests for ingestion service."""

from __future__ import annotations

import pytest
from queue import Queue
from unittest.mock import Mock, patch

from src.stream_service.application.dto import RawTick
from src.stream_service.application.services import IngestionService
from src.stream_service.domain.models import Instrument, Tick
from src.stream_service.infrastructure.redis_cache import RedisLatestPriceCache
from src.stream_service.infrastructure.postgres_repository import PostgresRepository


class TestIngestionService:
    """Test suite for IngestionService."""

    @pytest.fixture
    def ingestion_service(self, postgres_repo, redis_cache):
        """Create IngestionService with mocked repositories."""
        return IngestionService(
            instrument_repo=postgres_repo,
            tick_repo=postgres_repo,
            price_cache=redis_cache,
            batch_size=2,
            flush_interval_seconds=0.1,
        )

    @pytest.fixture
    def sample_instruments(self):
        """Sample instruments for testing."""
        return [
            Instrument(
                isin="INE001",
                instrument_key="NSE_EQ|INE001",
                exchange="NSE",
                trading_symbol="EQ1",
                instrument_name="Equity 1",
                metadata={},
                id=1,
            ),
            Instrument(
                isin="INE002",
                instrument_key="NSE_EQ|INE002",
                exchange="NSE",
                trading_symbol="EQ2",
                instrument_name="Equity 2",
                metadata={},
                id=2,
            ),
        ]

    def test_start_and_stop(self, ingestion_service, sample_instruments):
        """Test service start/stop lifecycle."""
        ingestion_service.start(sample_instruments)
        assert ingestion_service._worker.is_alive()
        ingestion_service.stop()
        assert not ingestion_service._worker.is_alive()

    def test_enqueue_and_flush(self, ingestion_service, sample_instruments):
        """Test tick enqueue and batch flushing."""
        ingestion_service.start(sample_instruments)
        raw = RawTick(
            instrument_key="NSE_EQ|INE001",
            ltp=100.5,
            ltt_epoch_ms=1704110200000,
        )
        ingestion_service.enqueue(raw)
        ingestion_service.stop()
        # Verify tick was processed by checking queue size after stop
        assert ingestion_service._queue.empty()

    def test_unknown_instrument_logged(self, ingestion_service, caplog):
        """Test that unknown instrument_key is logged and skipped."""
        ingestion_service.start(sample_instruments)
        raw = RawTick(
            instrument_key="UNKNOWN",
            ltp=100.5,
            ltt_epoch_ms=1704110200000,
        )
        ingestion_service.enqueue(raw)
        ingestion_service.stop()
        assert "Unknown instrument_key UNKNOWN" in caplog.text
