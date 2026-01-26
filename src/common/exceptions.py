"""Custom exception hierarchy for MarketMonitor."""

from __future__ import annotations


class MarketMonitorError(Exception):
    """Base exception for all MarketMonitor errors."""


class ConfigurationError(MarketMonitorError):
    """Raised when required configuration is missing or invalid."""


class AuthenticationError(MarketMonitorError):
    """Raised for OAuth or authentication failures."""


class DataIngestionError(MarketMonitorError):
    """Raised during data ingestion or persistence failures."""


class ExternalServiceError(MarketMonitorError):
    """Raised when an external service (Upstox, Zerodha) is unavailable."""


class ValidationError(MarketMonitorError):
    """Raised for invalid input data (e.g., malformed ISIN)."""
