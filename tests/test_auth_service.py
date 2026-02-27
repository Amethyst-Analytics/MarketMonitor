"""Tests for OAuth service."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from src.auth_service.oauth_client import OAuthClient
from src.common.config import UpstoxConfig
from src.common.exceptions import AuthenticationError


class TestOAuthClient:
    """Test suite for OAuthClient."""

    @pytest.fixture
    def oauth_config(self):
        """
        Provide a minimal UpstoxConfig prefilled with test client credentials and redirect details.
        
        Returns:
            UpstoxConfig: configuration with client_id="test_id", client_secret="test_secret", redirect_host="localhost", redirect_port=8080, redirect_path="/upstox_auth"
        """
        return UpstoxConfig(
            client_id="test_id",
            client_secret="test_secret",
            redirect_host="localhost",
            redirect_port=8080,
            redirect_path="/upstox_auth",
        )

    @pytest.fixture
    def oauth_client(self, oauth_config):
        """
        Create an OAuthClient configured with the provided OAuth configuration.
        
        Parameters:
        	oauth_config (UpstoxConfig): Configuration containing client credentials and redirect information used to instantiate the OAuth client.
        
        Returns:
        	OAuthClient: An OAuthClient instance configured with `oauth_config`.
        """
        return OAuthClient(oauth_config)

    def test_build_authorization_url(self, oauth_client):
        """Test authorization URL construction."""
        url = oauth_client.build_authorization_url()
        assert "client_id=test_id" in url
        assert "redirect_uri=http://localhost:8080/upstox_auth" in url

    @patch("src.auth_service.oauth_client.webbrowser.open")
    def test_run_flow_success(self, mock_open, oauth_client):
        """Test successful OAuth flow."""
        mock_response = {"access_token": "test_token"}
        with patch.object(
            oauth_client, "_wait_for_auth_code", return_value="code123"
        ), patch.object(
            oauth_client, "_exchange_code_for_token", return_value=mock_response
        ):
            result = oauth_client.run_flow(open_browser=False)
            assert result["access_token"] == "test_token"

    def test_run_flow_timeout(self, oauth_client):
        """Test OAuth flow timeout."""
        with patch.object(
            oauth_client, "_wait_for_auth_code", side_effect=TimeoutError
        ):
            with pytest.raises(TimeoutError):
                oauth_client.run_flow(timeout=0.1)

    def test_exchange_failure(self, oauth_client):
        """Test token exchange failure."""
        with patch.object(
            oauth_client, "_wait_for_auth_code", return_value="code123"
        ), patch.object(
            oauth_client, "_exchange_code_for_token", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception):
                oauth_client.run_flow(open_browser=False)
