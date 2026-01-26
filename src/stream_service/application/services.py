"""Application-layer service orchestrating ingestion, batching, and persistence."""

from __future__ import annotations

import queue
import threading
import time
from typing import Dict, Iterable, List, Optional

from src.common.config import DatabaseConfig, RedisConfig
from src.common.config import (
    load_database_config,
    load_redis_config,
    load_stream_config,
)
from src.common.logging import configure_logging
from src.stream_service.application.dto import RawTick
from src.stream_service.domain.models import Instrument, Tick
from src.stream_service.domain.repositories import (
    InstrumentRepository,
    LatestPriceCache,
    TickRepository,
)
from src.stream_service.infrastructure.postgres_repository import PostgresRepository
from src.stream_service.infrastructure.redis_cache import RedisLatestPriceCache


class IngestionService:
    """Orchestrates the ingestion pipeline: buffering, conversion, and persistence."""

    def __init__(
        self,
        instrument_repo: InstrumentRepository,
        tick_repo: TickRepository,
        price_cache: Optional[LatestPriceCache] = None,
        batch_size: int = 1000,
        flush_interval_seconds: float = 0.5,
    ) -> None:
        self.instrument_repo = instrument_repo
        self.tick_repo = tick_repo
        self.price_cache = price_cache
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds

        self.logger = configure_logging(__name__)
        self._queue: queue.Queue[Optional[RawTick]] = queue.Queue()
        self._stop_event = threading.Event()
        self._instrument_key_to_id: Dict[str, int] = {}
        self._worker = threading.Thread(
            target=self._run, name="IngestionWorker", daemon=True
        )

    def start(self, instruments: Iterable[Instrument]) -> None:
        """Prime the instrument lookup cache and start the background worker."""
        self._instrument_key_to_id = {
            instrument.instrument_key: instrument.id
            for instrument in instruments
            if instrument.id is not None
        }
        self._worker.start()
        self.logger.info(
            "IngestionService started with %d instruments",
            len(self._instrument_key_to_id),
        )

    def enqueue(self, raw: RawTick) -> None:
        """Queue a raw tick for processing."""
        self._queue.put(raw)

    def stop(self) -> None:
        """Signal graceful shutdown and wait for the worker to finish."""
        if not self._stop_event.is_set():
            self._stop_event.set()
            self._queue.put(None)
            self._worker.join(timeout=10)
            self.logger.info("IngestionService stopped")

    def _run(self) -> None:
        buffer: List[Tick] = []
        last_flush = time.monotonic()

        while True:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                item = None

            if item is None:
                if self._stop_event.is_set() and not buffer:
                    break
            else:
                tick = self._to_tick(item)
                if tick:
                    buffer.append(tick)

            now = time.monotonic()
            should_flush = (
                len(buffer) >= self.batch_size
                or (buffer and now - last_flush >= self.flush_interval_seconds)
                or (self._stop_event.is_set() and buffer)
            )
            if should_flush and buffer:
                self._flush(buffer)
                buffer.clear()
                last_flush = now

        if buffer:
            self._flush(buffer)

    def _to_tick(self, raw: RawTick) -> Optional[Tick]:
        instrument_id = self._instrument_key_to_id.get(raw.instrument_key)
        if instrument_id is None:
            self.logger.warning("Unknown instrument_key %s", raw.instrument_key)
            return None
        return Tick(
            timestamp=epoch_ms_to_datetime(raw.ltt_epoch_ms),
            instrument_id=instrument_id,
            price=raw.ltp,
        )

    def _flush(self, ticks: List[Tick]) -> None:
        try:
            self.tick_repo.insert_ticks(ticks)
            if self.price_cache:
                for tick in ticks:
                    self.price_cache.upsert_price(tick)
            self.logger.debug("Flushed %d ticks", len(ticks))
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Failed to flush ticks: %s", exc)
