# Stream Service

Real-time market data ingestion service that connects to Upstox WebSocket API, processes tick data, and stores it in TimescaleDB with Redis caching.

## Architecture

### Layered Design

```
stream_service/
├─ domain/           # Business logic and models
│  ├─ models.py      # Instrument, Tick entities
│  └─ repositories.py # Repository interfaces
├─ application/      # Application services
│  ├─ services.py    # Ingestion orchestration
│  └─ dto.py         # Data transfer objects
├─ infrastructure/   # External adapters
│  ├─ postgres_repository.py # PostgreSQL implementation
│  ├─ redis_cache.py        # Redis cache implementation
│  └─ upstox_client.py      # WebSocket client wrapper
└─ presentation/     # CLI entrypoint
   └─ cli.py         # Command-line interface
```

## Components

### Domain Layer

#### Models (`domain/models.py`)

Core business entities:

```python
@dataclass
class Instrument:
    isin: str
    instrument_key: str
    exchange: str
    trading_symbol: str
    instrument_name: str
    metadata: Dict[str, Any]
    id: Optional[int] = None

@dataclass
class Tick:
    timestamp: datetime
    instrument_id: int
    price: float
```

#### Repositories (`domain/repositories.py`)

Abstract interfaces for data access:

```python
class InstrumentRepository(ABC):
    def upsert_instruments(self, instruments: Iterable[Instrument]) -> None: ...
    def resolve_instrument_id(self, instrument_key: str) -> int: ...
    def get_instrument_ids(self, instrument_keys: Iterable[str]) -> Dict[str, int]: ...

class TickRepository(ABC):
    def insert_ticks(self, ticks: Iterable[Tick]) -> None: ...

class LatestPriceCache(ABC):
    def upsert_price(self, tick: Tick) -> None: ...
```

### Application Layer

#### Ingestion Service (`application/services.py`)

Orchestrates the ingestion pipeline with batching and background processing:

```python
service = IngestionService(
    instrument_repo=repo,
    tick_repo=repo,
    price_cache=cache,
    batch_size=1000,
    flush_interval_seconds=0.5
)
service.start(instruments)
service.enqueue(raw_tick)
service.stop()
```

Features:

- **Background worker thread** for non-blocking processing
- **Configurable batching** by size and time
- **Graceful shutdown** with signal handling
- **Error handling** and logging

#### DTOs (`application/dto.py`)

Data transfer objects for external communication:

```python
@dataclass
class RawTick:
    instrument_key: str
    ltp: float
    ltt_epoch_ms: int
```

### Infrastructure Layer

#### PostgreSQL Repository (`infrastructure/postgres_repository.py`)

TimescaleDB implementation with optimized bulk operations:

```python
repo = PostgresRepository(db_config)
repo.upsert_instruments(instruments)
repo.insert_ticks(ticks)
```

Features:

- **Bulk upserts** for instruments
- **Batch inserts** for ticks with conflict resolution
- **Connection pooling** via psycopg2

#### Redis Cache (`infrastructure/redis_cache.py`)

Latest price cache for real-time dashboards:

```python
cache = RedisLatestPriceCache(redis_config)
cache.upsert_price(tick)
```

Features:

- **TTL-based expiration**
- **Connection resilience**
- **Structured JSON storage**

#### Upstox Client (`infrastructure/upstox_client.py`)

WebSocket client wrapper with reconnection logic:

```python
client = UpstoxStreamer(stream_config, on_tick=callback)
client.set_instruments(instrument_keys)
client.start()
client.wait()
```

Features:

- **Automatic reconnection**
- **Instrument subscription management**
- **Error handling** and logging

### Presentation Layer

#### CLI (`presentation/cli.py`)

Command-line interface for running the stream service:

```bash
# Run with instrument catalog
python -m stream_service --catalog complete_data_formatted.json

# Default catalog path
python -m stream_service
```

Features:

- **Instrument catalog loading**
- **Database upsert** of instruments
- **Graceful shutdown** on SIGINT/SIGTERM

## Configuration

Required environment variables:

```bash
UPSTOX_ACCESS_TOKEN="your_access_token"
UPSTOX_INSTRUMENT_FILE="complete_data_formatted.json"
UPSTOX_STREAM_MODE="ltpc"  # or "ltp"
UPSTOX_PG_DSN="postgresql://..."
UPSTOX_PG_BATCH="1000"
UPSTOX_PG_FLUSH_INTERVAL="0.5"
UPSTOX_REDIS_URL="redis://..."
UPSTOX_REDIS_TTL="10"
```

## Performance Tuning

### Batching Parameters

- **Batch Size**: Default 1000, increase for high-throughput
- **Flush Interval**: Default 0.5s, balance latency vs throughput

### Database Optimization

```sql
-- Create hypertable
SELECT create_hypertable('ticks', 'ts');

-- Add compression policy
ALTER TABLE ticks SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'instrument_id'
);

-- Add retention policy (optional)
SELECT add_retention_policy('ticks', INTERVAL '30 days');
```

### Redis Optimization

- **Pipeline commands** for bulk operations
- **Connection pooling** for high concurrency
- **Memory monitoring** for cache size

## Monitoring

### Metrics to Track

- **Ticks per second**: Ingestion rate
- **Batch size**: Average batch size
- **Queue depth**: Pending items count
- **Error rate**: Failed operations
- **Latency**: Time from receipt to storage

### Logging

Structured logging with context:

```python
logger.info(
    "Processed batch",
    extra={
        "batch_size": len(ticks),
        "duration_ms": duration,
        "instrument_count": len(instrument_ids)
    }
)
```

## Testing

```bash
# Run stream service tests
python -m pytest tests/test_stream_service.py -v

# Run specific test
python -m pytest tests/test_postgres_repository.py -v
```

### Test Categories

- **Unit Tests**: Repository implementations, service logic
- **Integration Tests**: End-to-end ingestion flow
- **Performance Tests**: Throughput and latency benchmarks

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check `UPSTOX_ACCESS_TOKEN` validity
   - Verify network connectivity
   - Check instrument subscription limits

2. **Database Errors**
   - Verify `UPSTOX_PG_DSN` connection string
   - Check TimescaleDB extension is installed
   - Monitor disk space

3. **Redis Connection Failed**
   - Verify `UPSTOX_REDIS_URL` format
   - Check Redis server status
   - Monitor memory usage

4. **High Memory Usage**
   - Reduce batch size
   - Increase flush frequency
   - Monitor queue depth

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("stream_service").setLevel(logging.DEBUG)
```

## Development

### Adding New Data Sources

1. Create new repository implementation
2. Implement required interfaces
3. Add configuration options
4. Write tests

### Custom Processing Logic

Extend `IngestionService` or create new application services:

```python
class CustomIngestionService(IngestionService):
    def _to_tick(self, raw: RawTick) -> Optional[Tick]:
        # Custom transformation logic
        return super()._to_tick(raw)
```

### Performance Profiling

```python
import cProfile
cProfile.run("service.start(instruments)")
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/
WORKDIR /app
CMD ["python", "-m", "stream_service"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: streamer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: streamer
  template:
    spec:
      containers:
        - name: streamer
          image: marketmonitor/streamer:latest
          envFrom:
            - secretRef:
                name: marketmonitor-secrets
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
```
