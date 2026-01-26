"""Production-ready OAuth helper for Upstox authentication."""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

import upstox_client
from upstox_client.rest import ApiException

from src.common.config import UpstoxConfig
from src.common.logging import configure_logging


class _AuthCodeHandler(BaseHTTPRequestHandler):
    """HTTP handler responsible for capturing the OAuth authorization code."""

    expected_path: str = "/upstox_auth"
    code_event: threading.Event = threading.Event()
    code_storage: Dict[str, Optional[str]] = {"code": None}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != self.expected_path:
            self.send_error(404, "Not Found")
            return

        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            self.send_error(400, "Missing code parameter")
            return

        self.code_storage["code"] = code
        self.code_event.set()

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Authorization received!</h2><p>You may close this tab.</p></body></html>"
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        """Silence default HTTP server logging to keep CLI output clean."""

        return


class OAuthClient:
    """High-level orchestrator for the Upstox OAuth flow."""

    def __init__(self, config: UpstoxConfig) -> None:
        self.config = config
        self.logger = configure_logging(__name__)
        self.api = upstox_client.LoginApi()

    def build_authorization_url(self) -> str:
        """Construct the URL the user must visit to grant consent."""

        return (
            "https://api.upstox.com/v2/login/authorization/dialog"
            f"?client_id={self.config.client_id}"
            f"&redirect_uri={self.config.redirect_uri}"
            "&response_type=code"
        )

    def _wait_for_auth_code(self, timeout: int = 180) -> str:
        """Run a temporary HTTP server to capture the redirect code."""

        _AuthCodeHandler.expected_path = self.config.redirect_path
        _AuthCodeHandler.code_storage = {"code": None}
        _AuthCodeHandler.code_event = threading.Event()

        server = HTTPServer(
            (self.config.redirect_host, self.config.redirect_port), _AuthCodeHandler
        )

        thread = threading.Thread(
            target=server.serve_forever, name="AuthCodeServer", daemon=True
        )
        thread.start()
        self.logger.info("Listening on %s", self.config.redirect_uri)

        event = _AuthCodeHandler.code_event
        if not event.wait(timeout=timeout):
            server.shutdown()
            thread.join()
            raise TimeoutError("Authorization code not received before timeout.")

        server.shutdown()
        thread.join()
        code = _AuthCodeHandler.code_storage.get("code")
        if not code:
            raise TimeoutError("Authorization code event triggered without data.")
        return code

    def _exchange_code_for_token(self, code: str) -> Dict:
        """Call Upstox token endpoint and return a JSON-serializable dict."""

        response = self.api.token(
            "2.0",
            code=code,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            redirect_uri=self.config.redirect_uri,
            grant_type="authorization_code",
        )
        if hasattr(response, "to_dict"):
            return response.to_dict()
        if isinstance(response, dict):
            return response
        return json.loads(json.dumps(response, default=str))

    def run_flow(self, timeout: int = 180, open_browser: bool = True) -> Dict:
        """Execute the OAuth flow and return the token payload."""

        auth_url = self.build_authorization_url()
        if open_browser:
            self.logger.info("Opening browser for OAuth consent...")
            webbrowser.open(auth_url)
        self.logger.info("If the browser did not open, copy this URL: %s", auth_url)

        code = self._wait_for_auth_code(timeout=timeout)
        self.logger.info("Authorization code captured: %s", code)
        return self._exchange_code_for_token(code)
