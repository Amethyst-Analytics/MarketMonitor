"""Shared helper functions used across services."""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["epoch_ms_to_datetime"]


def epoch_ms_to_datetime(epoch_ms: int) -> datetime:
    """Convert epoch milliseconds to an aware UTC datetime."""
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
