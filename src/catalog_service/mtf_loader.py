"""Utility to fetch Zerodha MTF securities and update tracking status."""

from __future__ import annotations

import json
from typing import Dict

import requests

from src.common.config import load_database_config
from src.common.logging import configure_logging
from src.stream_service.infrastructure.postgres_repository import PostgresRepository

ZERODHA_MTF_URL = "https://public.zrd.sh/crux/approved-mtf-securities.json"


def fetch_mtf_securities(url: str = ZERODHA_MTF_URL) -> Dict[str, dict]:
    """Fetch the latest Zerodha MTF list and return a dict keyed by ISIN."""
    logger = configure_logging(__name__)
    logger.info("Fetching MTF list from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # Normalize to ISIN-keyed dict for quick lookup
    isin_map = {
        entry.get("isin", "").upper(): entry for entry in data if entry.get("isin")
    }
    logger.info("Loaded %d MTF entries", len(isin_map))
    return isin_map


def sync_tracking_status(repo: PostgresRepository, mtf_map: Dict[str, dict]) -> None:
    """Update instruments.tracking_status based on MTF list presence."""
    logger = configure_logging(__name__)
    # NOTE: This assumes a `tracking_status` column exists on `instruments`.
    # For now we log actions; a future migration will add the column.
    active_isins = set(mtf_map.keys())
    logger.info("Marking %d ISINs as active based on MTF list", len(active_isins))
    # Placeholder: emit SQL to set tracking_status = true where isin IN active_isins
    # and false where NOT IN active_isins (soft deactivation).


def main() -> None:
    """CLI entrypoint to sync MTF tracking status."""
    logger = configure_logging(__name__)
    db_cfg = load_database_config()
    repo = PostgresRepository(db_cfg)

    mtf_map = fetch_mtf_securities()
    sync_tracking_status(repo, mtf_map)
    logger.info("MTF sync completed")


if __name__ == "__main__":
    main()
