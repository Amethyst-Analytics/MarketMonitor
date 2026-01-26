"""Repository interfaces for persistence and caching layers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable

from .models import Instrument, Tick


class InstrumentRepository(ABC):
    """Contract for instrument metadata storage."""

    @abstractmethod
    def upsert_instruments(self, instruments: Iterable[Instrument]) -> None:
        """Insert or update instrument records in bulk."""

    @abstractmethod
    def resolve_instrument_id(self, instrument_key: str) -> int:
        """Map an instrument key to its database identifier."""

    @abstractmethod
    def get_instrument_ids(self, instrument_keys: Iterable[str]) -> Dict[str, int]:
        """Return a mapping of instrument keys to database identifiers."""


class TickRepository(ABC):
    """Contract for tick persistence."""

    @abstractmethod
    def insert_ticks(self, ticks: Iterable[Tick]) -> None:
        """Persist a batch of ticks atomically."""


class LatestPriceCache(ABC):
    """Contract for caching the latest price per instrument."""

    @abstractmethod
    def upsert_price(self, tick: Tick) -> None:
        """Store or update the latest price snapshot for ``tick.instrument_id``."""
