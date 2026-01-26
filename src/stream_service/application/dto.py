"""Data transfer objects for the stream service application layer."""

from src.common.utils import epoch_ms_to_datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class RawTick:
    """Represents a feed update emitted by the Upstox websocket client."""

    instrument_key: str
    ltp: float
    ltt_epoch_ms: int
