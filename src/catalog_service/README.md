# Catalog Service

Manages instrument catalogs and MTF (Mutual Fund Transfer) securities synchronization from external data sources.

## Overview

The `catalog_service` module provides:

- **Upstox Catalog Loader**: Downloads and syncs complete instrument list
- **MTF Securities Loader**: Fetches Zerodha MTF approved securities
- **Database Integration**: Upserts instruments into PostgreSQL/TimescaleDB
- **CLI Tools**: Command-line interfaces for manual sync

## Components

### Upstox Loader (`upstox_loader.py`)

Downloads the complete Upstox instrument catalog and upserts it into the database.

#### Functions

```python
def download_catalog(url: str = UPSTOX_COMPLETE_DATA_URL) -> list[dict]:
    """Download and decompress the Upstox instrument catalog."""

def main() -> None:
    """CLI entrypoint for catalog loading."""
```

#### Usage

```bash
# Run catalog service
python -m catalog_service

# Equivalent to:
python -c "from catalog_service.upstox_loader import main; main()"
```

#### Data Format

The catalog contains instrument records with these fields:

```json
{
  "instrument_key": "NSE_EQ|INE002A01018",
  "exchange": "NSE",
  "trading_symbol": "INFY",
  "isin": "INE002A01018",
  "name": "Infosys Limited",
  "instrument_type": "EQ"
}
```

### MTF Loader (`mtf_loader.py`)

Fetches Zerodha MTF approved securities and updates tracking status.

#### Functions

```python
def fetch_mtf_securities(url: str = ZERODHA_MTF_URL) -> Dict[str, dict]:
    """Fetch the latest Zerodha MTF list and return a dict keyed by ISIN."""

def update_tracking_status(mtf_data: Dict[str, dict]) -> None:
    """Update tracking_status for MTF securities in the database."""

def main() -> None:
    """CLI entrypoint for MTF sync."""
```

#### Usage

```bash
# Run MTF sync
python -m catalog_service.mtf_loader

# Or directly:
python -c "from catalog_service.mtf_loader import main; main()"
```

#### Data Format

MTF securities data structure:

```json
{
  "INE002A01018": {
    "name": "Infosys Limited",
    "category": "Large Cap",
    "amc": "HDFC",
    "scheme": "HDFC MFT"
  }
}
```

## Configuration

Required environment variables:

```bash
UPSTOX_PG_DSN="postgresql://postgres:postgres@localhost:5432/market_data"
```

Optional for Upstox catalog:

```bash
UPSTOX_INSTRUMENT_FILE="complete_data_formatted.json"
```

## Database Schema

### Instruments Table

```sql
CREATE TABLE instruments (
    id SERIAL PRIMARY KEY,
    instrument_key VARCHAR(255) UNIQUE NOT NULL,
    instrument_name VARCHAR(255),
    exchange VARCHAR(50),
    isin VARCHAR(50),
    trading_symbol VARCHAR(255),
    tracking_status BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### MTF Securities Table

```sql
CREATE TABLE mtf_securities (
    isin VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    category VARCHAR(100),
    amc VARCHAR(100),
    scheme VARCHAR(255),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tracking Overrides Table

```sql
CREATE TABLE tracking_overrides (
    isin VARCHAR(50) PRIMARY KEY,
    tracking_status BOOLEAN NOT NULL,
    reason TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Automation

### Cron Jobs

Set up automated synchronization:

```bash
# Daily Upstox catalog sync at 2 AM
0 2 * * * python -m catalog_service

# Weekly MTF sync on Sundays at 3 AM
0 3 * * 0 python -m catalog_service.mtf_loader
```

### Kubernetes CronJobs

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: catalog-sync
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: catalog-sync
              image: marketmonitor/catalog-service:latest
              command: ["python", "-m", "catalog_service"]
              envFrom:
                - secretRef:
                    name: marketmonitor-secrets
          restartPolicy: OnFailure
```

## Performance Considerations

### Large Catalogs

- **Batch Processing**: Process instruments in batches of 1000
- **Transaction Management**: Use transactions for consistency
- **Indexing**: Ensure proper indexes on `instrument_key` and `isin`

### Network Optimization

- **Compression**: Upstox catalog is gzip compressed
- **Timeouts**: Set appropriate timeouts for HTTP requests
- **Retries**: Implement exponential backoff for failures

## Error Handling

### Common Scenarios

1. **Network Failure**
   - Retry with exponential backoff
   - Log detailed error information
   - Send alert if persistent

2. **Database Errors**
   - Use transactions for atomicity
   - Implement connection pooling
   - Log SQL errors for debugging

3. **Data Validation Errors**
   - Skip invalid records with warnings
   - Track validation statistics
   - Report data quality issues

### Monitoring Metrics

- **Catalog Size**: Number of instruments
- **Sync Duration**: Time taken for full sync
- **Error Rate**: Failed records percentage
- **Update Frequency**: How often catalog changes

## Testing

```bash
# Run catalog service tests
python -m pytest tests/test_catalog_service.py -v

# Test specific loader
python -m pytest tests/test_upstox_loader.py -v
```

### Test Data

Create test fixtures with sample data:

```python
@pytest.fixture
def sample_catalog():
    return [
        {
            "instrument_key": "NSE_EQ|INE001",
            "exchange": "NSE",
            "trading_symbol": "TEST",
            "isin": "INE001",
            "name": "Test Instrument"
        }
    ]
```

## Troubleshooting

### Common Issues

1. **Download Failed**
   - Check internet connectivity
   - Verify URL is accessible
   - Check firewall settings

2. **Database Connection Failed**
   - Verify `UPSTOX_PG_DSN` is correct
   - Check database server is running
   - Verify credentials

3. **Memory Issues**
   - Process catalog in smaller batches
   - Increase available memory
   - Use streaming for large files

4. **Duplicate Instruments**
   - Ensure unique constraints on `instrument_key`
   - Use upsert operations
   - Handle conflicts gracefully

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("catalog_service").setLevel(logging.DEBUG)
```

## Development

### Adding New Data Sources

1. Create new loader module
2. Implement standard interface:
   - `fetch_data()`: Download data
   - `transform_data()`: Convert to standard format
   - `upsert_data()`: Store in database
3. Add CLI entrypoint
4. Write comprehensive tests

### Custom Transformations

Extend the transformation logic:

```python
def transform_instrument(raw: dict) -> Instrument:
    # Custom transformation logic
    return Instrument(
        instrument_key=raw["instrument_key"],
        exchange=raw["exchange"],
        # ... other fields
    )
```

### Validation Rules

Add custom validation:

```python
def validate_instrument(instrument: Instrument) -> bool:
    if not instrument.isin:
        return False
    if len(instrument.isin) != 12:
        return False
    return True
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/
WORKDIR /app
CMD ["python", "-m", "catalog_service"]
```

### Kubernetes

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: catalog-sync
spec:
  template:
    spec:
      containers:
        - name: catalog-sync
          image: marketmonitor/catalog-service:latest
          command: ["python", "-m", "catalog_service"]
          envFrom:
            - secretRef:
                name: marketmonitor-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
      restartPolicy: OnFailure
```
