"""Tests for configuration loading and validation."""

from __future__ import annotations

import os
import pytest

from src.common.exceptions import ConfigurationError
from src.common.validator import validate_required_env_vars, validate_configs


def test_validate_required_env_vars_success(monkeypatch):
    """Test successful validation when all required vars are present."""
    monkeypatch.setenv("UPSTOX_CLIENT_ID", "test")
    monkeypatch.setenv("UPSTOX_CLIENT_SECRET", "test")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test")
    monkeypatch.setenv("UPSTOX_PG_DSN", "postgresql://test")
    monkeypatch.setenv("UPSTOX_REDIS_URL", "redis://localhost")
    validate_required_env_vars()  # Should not raise


def test_validate_required_env_vars_missing(monkeypatch):
    """Test validation failure when required vars are missing."""
    monkeypatch.delenv("UPSTOX_CLIENT_ID", raising=False)
    with pytest.raises(
        ConfigurationError, match="Missing required environment variables"
    ):
        validate_required_env_vars()


def test_validate_configs_success(monkeypatch):
    """Test successful configuration loading."""
    monkeypatch.setenv("UPSTOX_CLIENT_ID", "test")
    monkeypatch.setenv("UPSTOX_CLIENT_SECRET", "test")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test")
    monkeypatch.setenv("UPSTOX_PG_DSN", "postgresql://test")
    monkeypatch.setenv("UPSTOX_REDIS_URL", "redis://localhost")
    validate_configs()  # Should not raise
