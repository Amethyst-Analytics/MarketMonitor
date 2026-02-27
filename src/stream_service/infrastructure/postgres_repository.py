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
        """
        Initialize the repository with database configuration and prepare a module logger.
        
        Parameters:
            config (DatabaseConfig): Database connection configuration (DSN, credentials, and other connection settings) used for creating connections.
        """
        self.config = config
        self.logger = configure_logging(__name__)

    def _connect(self):
        """
        Create a new database connection using the repository's configured DSN.
        
        Returns:
            connection: A new psycopg2 connection connected to the configured DSN.
        """
        return psycopg2.connect(self.config.dsn)

    def upsert_instruments(self, instruments: Iterable[Instrument]) -> None:
        """
        Upserts a collection of instruments into the instruments table, inserting new rows or updating existing rows on key conflict.
        
        Inserts each instrument as a row with fields (instrument_key, instrument_name, exchange, isin, trading_symbol, metadata). When an instrument has no `instrument_name` attribute, `trading_symbol` is used for the `instrument_name` column. If the input iterable is empty, the function performs no database operations.
        
        Parameters:
            instruments (Iterable[Instrument]): Iterable of Instrument objects to insert or update.
        """
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
        """
        Retrieve the numeric database id for an instrument by its instrument_key.
        
        Parameters:
            instrument_key (str): The unique lookup key of the instrument.
        
        Returns:
            instrument_id (int): The database id for the matching instrument.
        
        Raises:
            KeyError: If no instrument with the given `instrument_key` exists.
        """
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
        """
        Retrieve instrument IDs for the given instrument keys.
        
        Parameters:
            instrument_keys (Iterable[str]): Iterable of instrument_key values to look up.
        
        Returns:
            Dict[str, int]: Mapping from each found instrument_key to its numeric `id`. Keys not present in the database are omitted.
        """
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
        """
        Upserts tick records into the database ticks table.
        
        Inserts each Tick's timestamp, instrument_id, and price; on conflict of (ts, instrument_id) updates the price and sets received_at to the current time. If the provided iterable is empty, the function returns without performing any database operations.
        
        Parameters:
            ticks (Iterable[Tick]): Iterable of Tick objects whose `timestamp`, `instrument_id`, and `price` fields will be stored.
        """
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
