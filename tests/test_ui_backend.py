"""Tests for UI backend API."""

from __future__ import annotations

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.ui.backend.api import app
from src.ui.backend.services import get_auth_status, list_subscribed_instruments


class TestUIBackendAPI:
    """Test suite for FastAPI backend."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_auth_status_has_token(self, client, monkeypatch):
        """Test /auth/status when token is present."""
        monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test_token")
        response = client.get("/auth/status")
        assert response.status_code == 200
        assert response.json() == {"has_token": True}

    def test_auth_status_no_token(self, client, monkeypatch):
        """Test /auth/status when token is missing."""
        monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
        response = client.get("/auth/status")
        assert response.status_code == 200
        assert response.json() == {"has_token": False}

    def test_instruments_subscribed(self, client):
        """Test /instruments/subscribed endpoint."""
        response = client.get("/instruments/subscribed")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_bulk_isin_endpoint(self, client):
        """Test POST /isin/bulk endpoint."""
        payload = {"isins": ["INE001", "INE002"]}
        response = client.post("/isin/bulk", json=payload)
        assert response.status_code == 200
        assert "added" in response.json()
        assert "removed" in response.json()
        assert "errors" in response.json()
