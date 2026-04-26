# MarketMonitor — Agent Rules

> Repo-specific rules for Claude Code and Gemini CLI. Read `../CLAUDE.md` and `../GEMINI.md` first — this file extends those, it does not replace them.

---

## Purpose

MarketMonitor has **one job**: ingest tick data from the Upstox WebSocket, write it to TimescaleDB, and publish it to Redis. It also exposes a minimal control HTTP API (start/stop) on port 8001.

---

## Stack

| Item | Detail |
|---|---|
| Language | Python 3.11.x |
| Package manager | Poetry 1.7.x |
| Package name | `market_monitor` |
| DB | PostgreSQL 16 + TimescaleDB 2.13.x (via `asyncpg`) |
| Cache / Pub-Sub | Redis 7.2 (via `aioredis`) |
| Control API | FastAPI on port 8001 (internal only, not exposed to UI) |
| Shared lib | `amethyst_core` (local path dependency) |

---

## Tables Owned by This Service

MarketMonitor is the **sole writer** to these tables. No other service may write to them.

| Table | Type | Notes |
|---|---|---|
| `instruments` | Regular table | Master list of tracked stocks |
| `ticks` | TimescaleDB hypertable | Raw tick data, partitioned by day |

See `codeplan.md` §5 for the exact DDL. Do not alter column names, types, or primary keys.

---

## File Structure

```
MarketMonitor/
├── src/market_monitor/
│   ├── main.py                # asyncio.run(main()) entry point
│   ├── config.py              # Extends AmethystBaseConfig
│   ├── service.py             # Extends BaseService, orchestrates components
│   ├── sync_instruments.py    # Fetch Upstox instrument JSON, filter, populate DB
│   ├── control/api.py         # FastAPI control app (port 8001)
│   ├── streaming/
│   │   ├── upstox_client.py   # Upstox WebSocket client
│   │   ├── processor.py       # Validates and transforms raw tick data
│   │   └── batch_writer.py    # Batches and writes to PostgreSQL
│   ├── storage/
│   │   ├── tick_repository.py
│   │   └── instrument_repository.py
│   └── publisher.py           # Redis Pub/Sub + cache update
├── migrations/                # Alembic migrations
├── tests/
├── Dockerfile
└── pyproject.toml
```

---

## Naming Conventions

- All transforms: verb phrases — `normalize_tick()`, `filter_inactive_instruments()`
- Repository methods: noun phrases — `get_instrument_by_symbol()`, `insert_tick_batch()`
- Side-effect functions: verb prefix — `write_tick_batch()`, `publish_to_redis()`

---

## Forbidden Patterns

- No direct imports from `amethyst_server` or `amethyst_analytics`
- No SQLite — PostgreSQL 16 only
- No synchronous DB or Redis calls — everything is `async/await`
- No hardcoded instrument keys or symbols — all come from the DB or Upstox API
- No raw SQL with f-strings — use parameterised `asyncpg` queries only
- No loading the entire instrument list into memory at peak — stream or batch

---

## Critical Rules

- `BatchWriter` must use `ON CONFLICT DO NOTHING` on the composite PK `(ts, instrument_id, tick_id)` — duplicate ticks from reconnects must be silently dropped.
- `tick_id` is a UUID generated at ingestion time — never reuse or derive from tick content.
- `MarketMonitor` must poll the DB for a valid Upstox `access_token` before connecting the WebSocket. It must not hard-fail on startup if the token is absent — retry with backoff.
- All timestamps stored in `TIMESTAMPTZ` UTC. Never convert to IST.

---

## Testing

- `processor.py` transforms must be pure — test with synthetic tick dicts, no network.
- `batch_writer.py` integration test: use `testcontainers` with real TimescaleDB.
- `upstox_client.py`: mock the WebSocket; test reconnect/backoff logic.
- Pipeline stage tests must cover: valid input, empty input, malformed records, schema mismatch.
- Coverage minimum: 80% (CI hard fails below this).

---

## Service Boundaries

| Direction | Protocol | Notes |
|---|---|---|
| Upstox → MarketMonitor | WebSocket (WSS) | Upstox market data feed |
| MarketMonitor → PostgreSQL | asyncpg | Batch writes to `ticks` and `instruments` |
| MarketMonitor → Redis | aioredis Pub/Sub + SET | Tick cache and live stream |
| AmethystServer → MarketMonitor | REST (port 8001) | Control API only (start/stop) |

MarketMonitor never calls AmethystServer. Communication is one-way for control.
