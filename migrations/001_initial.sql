-- Initial schema for MarketMonitor
-- Run via psql -U postgres -d market_data -f migrations/001_initial.sql

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Instruments dimension table
CREATE TABLE IF NOT EXISTS instruments (
    id SERIAL PRIMARY KEY,
    isin TEXT,
    instrument_key TEXT UNIQUE NOT NULL,
    exchange TEXT,
    exchange_token TEXT,
    trading_symbol TEXT,
    instrument_name TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    tracking_status BOOLEAN DEFAULT false,
    tracking_source TEXT DEFAULT 'manual'
);

-- Ticks hypertable for time-series data
CREATE TABLE IF NOT EXISTS ticks (
    ts TIMESTAMPTZ NOT NULL,
    instrument_id INT NOT NULL REFERENCES instruments(id),
    price DOUBLE PRECISION NOT NULL,
    received_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (ts, instrument_id)
);

SELECT create_hypertable('ticks', 'ts', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX ON ticks (instrument_id, ts DESC);

-- MTF securities table (for tracking overrides)
CREATE TABLE IF NOT EXISTS mtf_securities (
    id SERIAL PRIMARY KEY,
    isin TEXT UNIQUE NOT NULL,
    source_payload JSONB,
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT true
);

-- Manual tracking overrides
CREATE TABLE IF NOT EXISTS tracking_overrides (
    id SERIAL PRIMARY KEY,
    isin TEXT NOT NULL,
    added_by TEXT,
    reason TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit snapshots for feeds
CREATE TABLE IF NOT EXISTS feed_snapshots (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT now(),
    etag TEXT,
    payload JSONB,
    checksum TEXT
);

-- Token audit log
CREATE TABLE IF NOT EXISTS token_audit (
    id SERIAL PRIMARY KEY,
    issued_at TIMESTAMPTZ DEFAULT now(),
    operator TEXT,
    expires_at TIMESTAMPTZ,
    notes TEXT
);

-- Triggers to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_instruments_updated_at BEFORE UPDATE
    ON instruments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
