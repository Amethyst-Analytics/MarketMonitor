"""Repository interfaces for persistence and caching layers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable

from .models import Instrument, Tick


class InstrumentRepository(ABC):
    """Contract for instrument metadata storage."""

    @abstractmethod
    def upsert_instruments(self, instruments: Iterable[Instrument]) -> None:
        """
        Upserts multiple instrument metadata records.
        
        Parameters:
            instruments (Iterable[Instrument]): Iterable of Instrument domain objects to insert or update in the repository. Existing records will be updated and missing records will be created.
        """

    @abstractmethod
    def resolve_instrument_id(self, instrument_key: str) -> int:
        """
        Map an external instrument key to its persistent database identifier.
        
        Parameters:
            instrument_key (str): External unique key identifying an instrument.
        
        Returns:
            int: Database identifier for the instrument.
        """

    @abstractmethod
    def get_instrument_ids(self, instrument_keys: Iterable[str]) -> Dict[str, int]:
        """
        Return a mapping of instrument keys to their database identifiers.
        
        Parameters:
            instrument_keys (Iterable[str]): Iterable of instrument key strings to resolve.
        
        Returns:
            Dict[str, int]: Mapping where each provided instrument key present in the repository maps to its integer database identifier.
        """


class TickRepository(ABC):
    """Contract for tick persistence."""

    @abstractmethod
    def insert_ticks(self, ticks: Iterable[Tick]) -> None:
        """
        Persist a batch of ticks atomically.
        
        Parameters:
            ticks (Iterable[Tick]): Iterable of Tick objects to persist; all provided ticks are stored as a single atomic operation.
        """


class LatestPriceCache(ABC):
    """Contract for caching the latest price per instrument."""

    @abstractmethod
    def upsert_price(self, tick: Tick) -> None:
        """
        Store or update the latest price snapshot for the instrument referenced by the provided tick.
        
        Parameters:
            tick (Tick): Tick containing the instrument identifier and the latest price snapshot to store.
        """
