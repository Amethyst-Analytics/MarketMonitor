"""Tests for PostgreSQL repository implementation."""

from __future__ import annotations

import pytest
from datetime import datetime

from src.stream_service.domain.models import Instrument, Tick
from src.stream_service.infrastructure.postgres_repository import PostgresRepository


class TestPostgresRepository:
    """Test suite for PostgresRepository."""

    def test_upsert_instruments(self, postgres_repo, sample_instrument):
        """Test instrument upsert."""
        postgres_repo.upsert_instruments([sample_instrument])
        # Verify by resolving ID
        instrument_id = postgres_repo.resolve_instrument_id(
            sample_instrument.instrument_key
        )
        assert instrument_id is not None

    def test_get_instrument_ids(self, postgres_repo, sample_instrument):
        """Test bulk instrument ID resolution."""
        postgres_repo.upsert_instruments([sample_instrument])
        ids = postgres_repo.get_instrument_ids([sample_instrument.instrument_key])
        assert sample_instrument.instrument_key in ids

    def test_insert_ticks(self, postgres_repo, sample_instrument):
        """
        Verifies that inserting ticks for an upserted instrument completes without raising an exception.
        
        Sets up the instrument, resolves its ID, and attempts to insert a tick; the test passes if no exception is raised.
        """
        postgres_repo.upsert_instruments([sample_instrument])
        instrument_id = postgres_repo.resolve_instrument_id(
            sample_instrument.instrument_key
        )
        tick = Tick(
            timestamp=datetime.utcnow(),
            instrument_id=instrument_id,
            price=100.5,
        )
        postgres_repo.insert_ticks([tick])
        # No exception means success (integration test would verify DB state)
