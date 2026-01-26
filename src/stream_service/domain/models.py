"""Domain models governing stream ingestion workflows.

Purpose:
    Provide immutable structures for instruments and ticks so the application
    and infrastructure layers can exchange data without leaking persistence or
    transport-specific concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass(frozen=True)
class Instrument:
    """Rich representation of an instrument tracked by the streamer.

    Inputs:
        id: Optional database identifier (``None`` before persistence).
        isin: International Securities Identification Number.
        instrument_key: Upstox-specific instrument key used for subscriptions.
        exchange: Exchange code (e.g., ``NSE``).
        trading_symbol: Exchange trading symbol.
        instrument_name: Human-readable instrument name.
        metadata: Arbitrary metadata (JSON-serializable) from catalog sources.

    Outputs:
        Immutable dataclass consumed by repositories and services.

    Error Cases:
        None beyond standard dataclass validation.
    """

    isin: Optional[str]
    instrument_key: str
    exchange: str
    trading_symbol: str
    instrument_name: str
    metadata: Dict[str, str]
    id: Optional[int] = None


@dataclass(frozen=True)
class Tick:
    """Normalized tick payload ready for persistence and caching.

    Inputs:
        timestamp: UTC timestamp derived from LTT epoch milliseconds.
        instrument_id: Foreign key to ``instruments`` table.
        price: Last traded price for the instrument at ``timestamp``.

    Outputs:
        Immutable dataclass representing a single tick measurement.

    Error Cases:
        None beyond standard dataclass validation.
    """

    timestamp: datetime
    instrument_id: int
    price: float
