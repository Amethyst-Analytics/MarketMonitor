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
        """
        Initialize the UpstoxStreamer with streaming configuration and a callback to receive parsed ticks.
        
        Creates and configures the underlying API client and MarketDataStreamerV3, applies authentication from `config`, initializes internal subscription and lifecycle state, and registers websocket event handlers.
        
        Parameters:
            config (StreamConfig): Stream configuration containing at least `access_token` (Bearer token) and `mode` (streaming mode).
            on_tick (Callable[[RawTick], None]): Callback invoked for each normalized tick; receives a `RawTick` instance.
        """
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
        """
        Register the streamer's event callbacks so lifecycle, message, error, and reconnect events are routed to this instance's handler methods.
        
        This wires the following streamer events to their corresponding handlers: OPEN, MESSAGE, ERROR, CLOSE, RECONNECTING, and AUTO_RECONNECT_STOPPED.
        """
        ev = self.streamer.Event
        self.streamer.on(ev["OPEN"], self._on_open)
        self.streamer.on(ev["MESSAGE"], self._on_message)
        self.streamer.on(ev["ERROR"], self._on_error)
        self.streamer.on(ev["CLOSE"], self._on_close)
        self.streamer.on(ev["RECONNECTING"], self._on_reconnecting)
        self.streamer.on(ev["AUTO_RECONNECT_STOPPED"], self._on_auto_reconnect_stopped)

    def set_instruments(self, instrument_keys: List[str]) -> None:
        """
        Update the streamer's subscribed instruments and replace the internal subscription set.
        
        Parameters:
            instrument_keys (List[str]): List of instrument key strings to subscribe to; this replaces any previously set subscriptions.
        """
        self.instrument_key_set = set(instrument_keys)
        self.streamer.instrumentKeys = instrument_keys

    def start(self) -> None:
        """
        Establish the websocket connection and begin receiving market data from Upstox.
        """
        self.logger.info(
            "Connecting to Upstox market data feed (%s)...", self.config.mode.upper()
        )
        self.streamer.connect()

    def stop(self) -> None:
        """
        Signal shutdown and attempt to disconnect the websocket.
        
        Sets the internal stop event to request termination and calls the underlying streamer's disconnect method. If disconnect raises an exception, it is caught and a warning is logged.
        """
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
        """
        Log that the websocket connection has opened.
        """
        self.logger.info("Websocket opened")

    def _on_message(self, payload: Dict) -> None:
        """
        Process an incoming websocket payload and emit normalized tick events via the configured callback.
        
        Parses the payload's "feeds" mapping, filters entries to only those in the streamer's subscribed instrument set, and for each valid feed constructs a RawTick from the feed's `ltpc.ltp` and `ltpc.ltt` values (converting to float and int respectively). Invokes the `on_tick` callback with each constructed RawTick. Feeds missing required fields are ignored; parsing failures for individual feeds are logged and do not stop processing of other feeds.
        
        Parameters:
            payload (Dict): The raw websocket message payload expected to contain a "feeds" mapping of instrument keys to feed data.
        """
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
        """
        Handle streamer errors by logging the provided exception.
        
        Parameters:
            error (Exception): The exception that occurred in the streamer.
        """
        self.logger.error("Streamer error: %s", error)

    def _on_close(self, code: int, message: str) -> None:
        """
        Handle the websocket closure by logging the close details and signaling shutdown.
        
        Parameters:
            code (int): Numeric close code provided by the websocket.
            message (str): Human-readable reason for the closure.
        """
        self.logger.info("Websocket closed | code=%s | reason=%s", code, message)
        self.stop_event.set()

    def _on_reconnecting(self, details: str) -> None:
        """
        Log a warning when the streamer initiates an automatic reconnect attempt.
        
        Parameters:
            details (str): Human-readable information about the reconnect event (reason, state, or metadata).
        """
        self.logger.warning("Auto-reconnect: %s", details)

    def _on_auto_reconnect_stopped(self, reason: str) -> None:
        """
        Handle the streamer's auto-reconnect stopping by logging the reason and signaling shutdown.
        
        Logs the provided `reason` and sets the internal `stop_event` to indicate the streamer should stop.
        
        Parameters:
            reason (str): Human-readable reason why auto-reconnect was stopped.
        """
        self.logger.error("Auto-reconnect stopped: %s", reason)
        self.stop_event.set()
