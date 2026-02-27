"""Utility to download and upsert the Upstox complete instrument catalog."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import requests

from src.common.config import load_database_config
from src.common.logging import configure_logging
from src.stream_service.domain.models import Instrument
from src.stream_service.infrastructure.postgres_repository import PostgresRepository


UPSTOX_COMPLETE_DATA_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
)


def download_catalog(url: str = UPSTOX_COMPLETE_DATA_URL) -> list[dict]:
    """
    Download and decompress the Upstox instrument catalog from the given URL.
    
    Parses the gzipped JSON response into a list of catalog entry dictionaries.
    
    Returns:
        list[dict]: Parsed catalog entries.
    
    Raises:
        requests.HTTPError: If the HTTP response status is not successful.
    """
    logger = configure_logging(__name__)
    logger.info("Downloading catalog from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    raw = gzip.decompress(resp.content)
    data = json.loads(raw)
    logger.info("Loaded %d catalog entries", len(data))
    return data


def transform_to_instruments(raw: list[dict]) -> list[Instrument]:
    """
    Convert raw Upstox catalog entries into Instrument domain objects.
    
    Only entries containing an "instrument_key" are converted; entries missing that key are skipped.
    
    Parameters:
        raw (list[dict]): List of raw catalog entry dictionaries. Expected keys:
            - "instrument_key" (required)
            - "isin" (optional)
            - "exchange" (optional)
            - "trading_symbol" (optional)
            - "name" (optional)
            - "exchange_token" (optional)
    
    Returns:
        list[Instrument]: A list of Instrument objects built from the provided entries. Fields absent in an entry are populated with None or empty strings as appropriate.
    """
    instruments = []
    for entry in raw:
        if not entry.get("instrument_key"):
            continue
        instruments.append(
            Instrument(
                isin=entry.get("isin"),
                instrument_key=entry["instrument_key"],
                exchange=entry.get("exchange", ""),
                trading_symbol=entry.get("trading_symbol", ""),
                instrument_name=entry.get("name", ""),
                metadata={
                    "exchange_token": entry.get("exchange_token", ""),
                },
            )
        )
    return instruments


def main() -> None:
    """CLI entrypoint to refresh the Upstox instrument catalog."""
    logger = configure_logging(__name__)
    db_cfg = load_database_config()
    repo = PostgresRepository(db_cfg)

    raw = download_catalog()
    instruments = transform_to_instruments(raw)
    repo.upsert_instruments(instruments)
    logger.info("Catalog refresh completed: %d instruments upserted", len(instruments))


if __name__ == "__main__":
    main()
