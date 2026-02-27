"""Shared helper functions used across services."""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["epoch_ms_to_datetime"]


def epoch_ms_to_datetime(epoch_ms: int) -> datetime:
    """
    Convert epoch milliseconds since 1970-01-01T00:00:00Z to an aware UTC datetime.
    
    Parameters:
        epoch_ms (int): Milliseconds since the Unix epoch (1970-01-01T00:00:00Z).
    
    Returns:
        datetime: A timezone-aware `datetime` in UTC corresponding to the provided epoch milliseconds.
    """
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
