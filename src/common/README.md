# Common Module

Shared utilities, configuration, and infrastructure components used across all MarketMonitor services.

## Components

### Configuration (`config.py`)

Centralized configuration management with environment variable loading and validation.

#### Data Classes

```python
@dataclass
class UpstoxConfig:
    client_id: str
    client_secret: str
    redirect_host: str
    redirect_port: int
    redirect_path: str

@dataclass
class DatabaseConfig:
    dsn: str
    batch_size: int = 1000
    flush_interval_seconds: float = 0.5

@dataclass
class RedisConfig:
    url: str
    ttl: int = 10

@dataclass
class StreamConfig:
    mode: str = "ltpc"
```

#### Loading Functions

```python
def load_upstox_config() -> UpstoxConfig:
    """Load Upstox configuration from environment variables."""

def load_database_config() -> DatabaseConfig:
    """Load database configuration from environment variables."""

def load_redis_config() -> RedisConfig:
    """Load Redis configuration from environment variables."""

def load_stream_config() -> StreamConfig:
    """Load streaming configuration from environment variables."""
```

#### Usage

```python
from src.common.config import load_database_config

db_config = load_database_config()
print(f"Connecting to: {db_config.dsn}")
```

### Logging (`logging.py`)

Structured logging configuration with consistent formatting across services.

#### Configuration

```python
def configure_logging(name: str) -> logging.Logger:
    """Configure logger with consistent formatting."""

def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance."""
```

#### Usage

```python
from src.common.logging import configure_logging

logger = configure_logging(__name__)
logger.info("Service started")
logger.error("Error occurred", extra={"error_code": 500})
```

#### Log Format

```
2025-01-01 12:00:00,000 - module.name - INFO - Service started
2025-01-01 12:00:01,000 - module.name - ERROR - Error occurred [error_code=500]
```

### Exceptions (`exceptions.py`)

Custom exception hierarchy for structured error handling.

#### Exception Classes

```python
class MarketMonitorError(Exception):
    """Base exception for all MarketMonitor errors."""

class ConfigurationError(MarketMonitorError):
    """Raised when required configuration is missing or invalid."""

class AuthenticationError(MarketMonitorError):
    """Raised for OAuth or authentication failures."""

class DataIngestionError(MarketMonitorError):
    """Raised during data ingestion or persistence failures."""

class ExternalServiceError(MarketMonitorError):
    """Raised when an external service is unavailable."""

class ValidationError(MarketMonitorError):
    """Raised for invalid input data."""
```

#### Usage

```python
from src.common.exceptions import ConfigurationError

if not os.getenv("REQUIRED_VAR"):
    raise ConfigurationError("REQUIRED_VAR must be set")
```

### Validator (`validator.py`)

Runtime configuration validation to ensure all required environment variables are present.

#### Functions

```python
def validate_required_env_vars() -> None:
    """Validate that all required environment variables are present."""

def validate_configs() -> None:
    """Validate that configuration objects can be loaded and are coherent."""

def main() -> None:
    """CLI entrypoint for configuration validation."""
```

#### Usage

```bash
# Validate configuration
python -m src.common.validator

# Or programmatically
from src.common.validator import validate_configs
validate_configs()
```

### Utilities (`utils.py`)

Shared utility functions for common operations.

#### Functions

```python
def epoch_ms_to_datetime(epoch_ms: int) -> datetime:
    """Convert epoch milliseconds to an aware UTC datetime."""
```

#### Usage

```python
from src.common.utils import epoch_ms_to_datetime

dt = epoch_ms_to_datetime(1704110400000)
print(f"Converted datetime: {dt}")
```

## Environment Variables

### Required Variables

| Variable               | Description                  | Example                    |
| ---------------------- | ---------------------------- | -------------------------- |
| `UPSTOX_CLIENT_ID`     | Upstox OAuth client ID       | `your_client_id`           |
| `UPSTOX_CLIENT_SECRET` | Upstox OAuth client secret   | `your_client_secret`       |
| `UPSTOX_ACCESS_TOKEN`  | OAuth access token           | `eyJ...`                   |
| `UPSTOX_PG_DSN`        | PostgreSQL connection string | `postgresql://...`         |
| `UPSTOX_REDIS_URL`     | Redis connection URL         | `redis://localhost:6379/0` |

### Optional Variables

| Variable                   | Description              | Default                        |
| -------------------------- | ------------------------ | ------------------------------ |
| `UPSTOX_REDIRECT_HOST`     | OAuth redirect host      | `localhost`                    |
| `UPSTOX_REDIRECT_PORT`     | OAuth redirect port      | `8080`                         |
| `UPSTOX_REDIRECT_PATH`     | OAuth redirect path      | `/upstox_auth`                 |
| `UPSTOX_INSTRUMENT_FILE`   | Instrument catalog path  | `complete_data_formatted.json` |
| `UPSTOX_STREAM_MODE`       | Stream mode              | `ltpc`                         |
| `UPSTOX_PG_BATCH`          | DB batch size            | `1000`                         |
| `UPSTOX_PG_FLUSH_INTERVAL` | Flush interval (seconds) | `0.5`                          |
| `UPSTOX_REDIS_TTL`         | Redis TTL (seconds)      | `10`                           |

## Configuration Validation

### Validation Rules

1. **Required Variables**: Must be present and non-empty
2. **URL Formats**: Must be valid URLs
3. **Port Numbers**: Must be valid port ranges (1-65535)
4. **File Paths**: Must be accessible files
5. **Data Types**: Must be convertible to expected types

### Validation Examples

```python
# Valid configuration
UPSTOX_CLIENT_ID="valid_id"
UPSTOX_PG_DSN="postgresql://user:pass@host:5432/db"
UPSTOX_REDIS_URL="redis://localhost:6379/0"

# Invalid configuration
UPSTOX_CLIENT_ID=""  # Empty value
UPSTOX_PG_DSN="invalid://url"  # Invalid URL
UPSTOX_REDIRECT_PORT="99999"  # Invalid port
```

## Logging Best Practices

### Structured Logging

Use structured logging with context:

```python
logger.info(
    "Processing batch",
    extra={
        "batch_size": len(batch),
        "instrument_count": len(instruments),
        "processing_time_ms": duration
    }
)
```

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information about service operation
- **WARNING**: Unexpected situations that don't prevent operation
- **ERROR**: Error conditions that prevent operation
- **CRITICAL**: Critical errors that may cause service failure

### Error Logging

Log errors with context:

```python
try:
    process_data(data)
except Exception as exc:
    logger.error(
        "Failed to process data",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "data_size": len(data)
        },
        exc_info=True
    )
```

## Testing

### Configuration Tests

```python
def test_load_upstox_config(monkeypatch):
    monkeypatch.setenv("UPSTOX_CLIENT_ID", "test_id")
    monkeypatch.setenv("UPSTOX_CLIENT_SECRET", "test_secret")

    config = load_upstox_config()
    assert config.client_id == "test_id"
    assert config.client_secret == "test_secret"
```

### Validation Tests

```python
def test_validate_required_env_vars_success(monkeypatch):
    monkeypatch.setenv("UPSTOX_CLIENT_ID", "test")
    validate_required_env_vars()  # Should not raise

def test_validate_required_env_vars_missing(monkeypatch):
    monkeypatch.delenv("UPSTOX_CLIENT_ID", raising=False)
    with pytest.raises(ConfigurationError):
        validate_required_env_vars()
```

## Development Guidelines

### Adding New Configuration

1. Add data class to `config.py`
2. Add loading function
3. Add validation rules
4. Update documentation
5. Add tests

Example:

```python
@dataclass
class NewServiceConfig:
    api_key: str
    timeout: int = 30

def load_new_service_config() -> NewServiceConfig:
    api_key = os.getenv("NEW_SERVICE_API_KEY")
    if not api_key:
        raise ValueError("NEW_SERVICE_API_KEY must be set")

    timeout = int(os.getenv("NEW_SERVICE_TIMEOUT", "30"))
    return NewServiceConfig(api_key=api_key, timeout=timeout)
```

### Adding New Exceptions

1. Create exception class in `exceptions.py`
2. Inherit from appropriate base class
3. Add documentation
4. Update tests

Example:

```python
class NetworkError(MarketMonitorError):
    """Raised for network-related errors."""
    pass
```

### Adding New Utilities

1. Add function to `utils.py`
2. Add type hints
3. Add docstring
4. Add tests
5. Update `__all__`

Example:

```python
def format_currency(amount: float, currency: str = "INR") -> str:
    """Format amount as currency string."""
    return f"{currency} {amount:,.2f}"
```

## Performance Considerations

### Configuration Loading

- **Lazy Loading**: Load configuration only when needed
- **Caching**: Cache configuration objects
- **Validation**: Validate once at startup

### Logging

- **Async Logging**: Use async logging for high-throughput
- **Structured Format**: Use JSON format for log aggregation
- **Sampling**: Sample debug logs in production

### Error Handling

- **Exception Chaining**: Preserve original exception context
- **Error Aggregation**: Group similar errors
- **Rate Limiting**: Limit error notifications

## Security

### Environment Variables

- **No Secrets in Code**: Never hardcode secrets
- **Encryption**: Encrypt sensitive environment variables
- **Access Control**: Limit access to configuration files

### Logging Security

- **No Sensitive Data**: Never log passwords or tokens
- **Sanitization**: Sanitize log data
- **Access Control**: Restrict log file access

## Troubleshooting

### Common Issues

1. **Configuration Not Loading**
   - Check environment variable names
   - Verify file permissions
   - Check for typos in variable names

2. **Logging Not Working**
   - Check logger configuration
   - Verify log file permissions
   - Check log level settings

3. **Validation Failures**
   - Check required variables
   - Verify data formats
   - Check for missing dependencies

### Debug Mode

Enable debug mode:

```python
import os
os.environ["DEBUG"] = "1"

# Or set in environment
export DEBUG=1
```

## Best Practices

### Configuration

- **Environment First**: Use environment variables for configuration
- **Validation**: Validate all configuration at startup
- **Defaults**: Provide sensible defaults for optional values
- **Documentation**: Document all configuration options

### Logging

- **Structured**: Use structured logging with context
- **Levels**: Use appropriate log levels
- **Performance**: Consider async logging for high throughput
- **Security**: Never log sensitive information

### Error Handling

- **Specific**: Use specific exception types
- **Context**: Provide context in error messages
- **Recovery**: Provide recovery options when possible
- **Logging**: Log errors with sufficient detail
