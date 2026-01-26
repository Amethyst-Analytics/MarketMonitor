"""PostgreSQL/TimescaleDB repository implementation."""

from __future__ import annotations

from typing import Dict, Iterable

import psycopg2
from psycopg2.extras import execute_values

from src.common.config import DatabaseConfig
from src.common.logging import configure_logging
from src.stream_service.domain.models import Instrument, Tick
from src.stream_service.domain.repositories import InstrumentRepository, TickRepository


class PostgresRepository(InstrumentRepository, TickRepository):
    """Concrete repository backed by PostgreSQL/TimescaleDB."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.logger = configure_logging(__name__)

    def _connect(self):
        return psycopg2.connect(self.config.dsn)

    def upsert_instruments(self, instruments: Iterable[Instrument]) -> None:
        records = [
            (
                instrument.instrument_key,
                (
                    instrument.instrument_name
                    if hasattr(instrument, "instrument_name")
                    else instrument.trading_symbol
                ),
                instrument.exchange,
                instrument.isin,
                instrument.trading_symbol,
                instrument.metadata,
            )
            for instrument in instruments
        ]
        if not records:
            return
        with self._connect() as connection:
            with connection.cursor() as cursor:
                execute_values(
                    cursor,
                    """
                    INSERT INTO instruments (
                        instrument_key,
                        instrument_name,
                        exchange,
                        isin,
                        trading_symbol,
                        metadata
                    ) VALUES %s
                    ON CONFLICT (instrument_key) DO UPDATE
                        SET instrument_name = EXCLUDED.instrument_name,
                            exchange = EXCLUDED.exchange,
                            isin = EXCLUDED.isin,
                            trading_symbol = EXCLUDED.trading_symbol,
                            metadata = EXCLUDED.metadata
                    """,
                    records,
                )
            connection.commit()

    def resolve_instrument_id(self, instrument_key: str) -> int:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM instruments WHERE instrument_key = %s",
                    (instrument_key,),
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
        raise KeyError(f"Instrument {instrument_key} not found")

    def get_instrument_ids(self, instrument_keys: Iterable[str]) -> Dict[str, int]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                execute_values(
                    cursor,
                    "SELECT instrument_key, id FROM instruments WHERE instrument_key IN %s",
                    (tuple(instrument_keys),),
                )
                rows = cursor.fetchall()
                return {key: ident for key, ident in rows}

    def insert_ticks(self, ticks: Iterable[Tick]) -> None:
        rows = [(tick.timestamp, tick.instrument_id, tick.price) for tick in ticks]
        if not rows:
            return
        with self._connect() as connection:
            with connection.cursor() as cursor:
                execute_values(
                    cursor,
                    """
                    INSERT INTO ticks (ts, instrument_id, price)
                    VALUES %s
                    ON CONFLICT (ts, instrument_id) DO UPDATE
                        SET price = EXCLUDED.price,
                            received_at = now()
                    """,
                    rows,
                )
            connection.commit()
