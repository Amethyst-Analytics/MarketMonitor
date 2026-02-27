"""CLI entrypoint for the market data streaming service."""

from __future__ import annotations

import json
import signal
import sys

from src.common.config import (
    load_database_config,
    load_redis_config,
    load_stream_config,
)
from src.common.logging import configure_logging
from src.stream_service.application.dto import RawTick
from src.stream_service.application.services import IngestionService
from src.stream_service.domain.models import Instrument
from src.stream_service.infrastructure.postgres_repository import PostgresRepository
from src.stream_service.infrastructure.redis_cache import RedisLatestPriceCache
from src.stream_service.infrastructure.upstox_client import UpstoxStreamer


def load_instrument_catalog(path: str) -> list[Instrument]:
    """
    Load instruments from a JSON catalog file.
    
    Parses the JSON file at the given path and constructs an Instrument for each entry that contains an `instrument_key`. Entries without `instrument_key` are skipped. Each constructed Instrument includes `isin`, `instrument_key`, `exchange`, `trading_symbol`, `instrument_name`, and an empty `metadata` dict.
    
    Parameters:
        path (str): Path to the JSON catalog file.
    
    Returns:
        list[Instrument]: List of Instrument objects created from the catalog entries.
    """
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    instruments = []
    for e in entries:
        if not e.get("instrument_key"):
            continue
        instruments.append(
            Instrument(
                isin=e.get("isin"),
                instrument_key=e["instrument_key"],
                exchange=e.get("exchange", ""),
                trading_symbol=e.get("trading_symbol", ""),
                instrument_name=e.get("name", ""),
                metadata={},
            )
        )
    return instruments


def main() -> None:
    """
    Start the market data streaming and ingestion services and manage their lifecycle.
    
    Parses the CLI `--catalog` option, configures logging, loads stream/database/Redis settings,
    loads and upserts instrument metadata into the database, resolves database-assigned instrument IDs,
    and wires together the repositories, Redis price cache, ingestion service, and Upstox streamer.
    Registers SIGINT and SIGTERM handlers for graceful shutdown, starts the streamer and ingestion
    pipeline, and ensures both are stopped on exit.
    """
    parser = argparse.ArgumentParser(description="MarketMonitor stream service")
    parser.add_argument(
        "--catalog",
        default="complete_data_formatted.json",
        help="Path to the Upstox instrument catalog JSON.",
    )
    args = parser.parse_args()

    logger = configure_logging(__name__)

    # Load configurations
    stream_cfg = load_stream_config()
    db_cfg = load_database_config()
    redis_cfg = load_redis_config()

    # Load and upsert instruments
    instruments = load_instrument_catalog(args.catalog)
    instrument_repo = PostgresRepository(db_cfg)
    instrument_repo.upsert_instruments(instruments)

    # Resolve IDs after upsert so we have DB PKs
    key_to_id = instrument_repo.get_instrument_ids(
        [inst.instrument_key for inst in instruments]
    )
    instruments = [
        Instrument(
            isin=inst.isin,
            instrument_key=inst.instrument_key,
            exchange=inst.exchange,
            trading_symbol=inst.trading_symbol,
            instrument_name=inst.instrument_name,
            metadata=inst.metadata,
            id=key_to_id.get(inst.instrument_key),
        )
        for inst in instruments
    ]

    # Wire infrastructure
    tick_repo = PostgresRepository(db_cfg)
    price_cache = RedisLatestPriceCache(redis_cfg)
    ingestion = IngestionService(
        instrument_repo=instrument_repo,
        tick_repo=tick_repo,
        price_cache=price_cache,
        batch_size=db_cfg.batch_size,
        flush_interval_seconds=db_cfg.flush_interval_seconds,
    )
    ingestion.start(instruments)

    # Wire streamer
    def on_tick(raw: RawTick) -> None:
        """
        Forward an incoming raw market tick to the ingestion service queue.
        
        Parameters:
            raw (RawTick): The incoming market tick data to enqueue for ingestion.
        """
        ingestion.enqueue(raw)

    streamer = UpstoxStreamer(stream_cfg, on_tick=on_tick)
    streamer.set_instruments([inst.instrument_key for inst in instruments])

    # Graceful shutdown handling
    def _shutdown(signum, _frame):
        """
        Handle a shutdown signal by stopping the streamer and ingestion services and terminating the process.
        
        Parameters:
            signum (int): The signal number received.
            _frame: The current stack frame at the time the signal was raised (unused).
        """
        logger.info("Received signal %s; shutting down...", signum)
        streamer.stop()
        ingestion.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        streamer.start()
        streamer.wait()
    finally:
        streamer.stop()
        ingestion.stop()


if __name__ == "__main__":
    main()
