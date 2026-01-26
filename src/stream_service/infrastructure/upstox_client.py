"""Adapter wrapping the Upstox websocket client with logging and callbacks."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List

from upstox_client import ApiClient, MarketDataStreamerV3

from src.common.config import StreamConfig
from src.common.logging import configure_logging
from src.stream_service.application.dto import RawTick


class UpstoxStreamer:
    """Encapsulates the Upstox websocket client and emits normalized tick events."""

    def __init__(
        self, config: StreamConfig, on_tick: Callable[[RawTick], None]
    ) -> None:
        self.config = config
        self.logger = configure_logging(__name__)
        self.on_tick = on_tick

        api_client = ApiClient()
        api_client.configuration.access_token = config.access_token
        api_client.set_default_header("Authorization", f"Bearer {config.access_token}")

        self.streamer = MarketDataStreamerV3(
            api_client=api_client,
            instrumentKeys=[],
            mode=config.mode,
        )
        self.instrument_key_set: set[str] = set()
        self.stop_event = threading.Event()
        self._register_handlers()

    def _register_handlers(self) -> None:
        ev = self.streamer.Event
        self.streamer.on(ev["OPEN"], self._on_open)
        self.streamer.on(ev["MESSAGE"], self._on_message)
        self.streamer.on(ev["ERROR"], self._on_error)
        self.streamer.on(ev["CLOSE"], self._on_close)
        self.streamer.on(ev["RECONNECTING"], self._on_reconnecting)
        self.streamer.on(ev["AUTO_RECONNECT_STOPPED"], self._on_auto_reconnect_stopped)

    def set_instruments(self, instrument_keys: List[str]) -> None:
        """Update the set of instrument keys to subscribe to."""
        self.instrument_key_set = set(instrument_keys)
        self.streamer.instrumentKeys = instrument_keys

    def start(self) -> None:
        """Connect and begin streaming."""
        self.logger.info(
            "Connecting to Upstox market data feed (%s)...", self.config.mode.upper()
        )
        self.streamer.connect()

    def stop(self) -> None:
        """Gracefully close the websocket."""
        if not self.stop_event.is_set():
            self.stop_event.set()
        try:
            self.streamer.disconnect()
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("Streamer disconnect raised: %s", exc)

    def wait(self) -> None:
        """Block until a stop signal is received."""
        while not self.stop_event.is_set():
            time.sleep(0.5)

    def _on_open(self) -> None:
        self.logger.info("Websocket opened")

    def _on_message(self, payload: Dict) -> None:
        feeds = payload.get("feeds", {})
        for instrument_key, data in feeds.items():
            if instrument_key not in self.instrument_key_set:
                continue
            ltpc = data.get("ltpc", {})
            ltp = ltpc.get("ltp")
            ltt = ltpc.get("ltt")
            if ltp is None or ltt is None:
                continue
            try:
                raw_tick = RawTick(
                    instrument_key=instrument_key,
                    ltp=float(ltp),
                    ltt_epoch_ms=int(ltt),
                )
                self.on_tick(raw_tick)
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "Failed to parse tick for %s: %s", instrument_key, exc
                )

    def _on_error(self, error: Exception) -> None:
        self.logger.error("Streamer error: %s", error)

    def _on_close(self, code: int, message: str) -> None:
        self.logger.info("Websocket closed | code=%s | reason=%s", code, message)
        self.stop_event.set()

    def _on_reconnecting(self, details: str) -> None:
        self.logger.warning("Auto-reconnect: %s", details)

    def _on_auto_reconnect_stopped(self, reason: str) -> None:
        self.logger.error("Auto-reconnect stopped: %s", reason)
        self.stop_event.set()
