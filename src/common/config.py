"""Centralized configuration loader for MarketMonitor services.

Purpose:
    Expose typed dataclasses for environment-driven settings so each service
    reads configuration through a validated, single interface.

Error Cases:
    Raises ``ValueError`` when mandatory settings are missing or malformed.
"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class UpstoxConfig:
    """Encapsulates Upstox OAuth credentials and redirect metadata."""

    client_id: str
    client_secret: str
    redirect_host: str = "localhost"
    redirect_port: int = 8080
    redirect_path: str = "/upstox_auth"

    @property
    def redirect_uri(self) -> str:
        """
        Construct the full HTTP redirect URI from the configured host, port, and path.
        
        Returns:
            The full redirect URI as a string, for example "http://localhost:8080/upstox_auth".
        """

        return f"http://{self.redirect_host}:{self.redirect_port}{self.redirect_path}"


@dataclass(frozen=True)
class DatabaseConfig:
    """Holds TimescaleDB DSN and batching parameters."""

    dsn: str
    batch_size: int = 1000
    flush_interval_seconds: float = 0.5


@dataclass(frozen=True)
class RedisConfig:
    """Settings for the Redis latest-price cache layer."""

    url: str
    ttl_seconds: int = 10


@dataclass(frozen=True)
class SmtpConfig:
    """SMTP configuration for error-alert emails."""

    host: str
    port: int
    username: str
    password: str
    sender: str
    recipients: str


@dataclass(frozen=True)
class StreamConfig:
    """Settings required by the streaming ingestion service."""

    access_token: str
    instrument_file: str = "complete_data_formatted.json"
    mode: str = "ltpc"


def load_upstox_config() -> UpstoxConfig:
    """
    Load Upstox OAuth credentials and redirect settings from environment variables.
    
    Required environment variables:
    - UPSTOX_CLIENT_ID
    - UPSTOX_CLIENT_SECRET
    
    Optional environment variables with defaults:
    - UPSTOX_REDIRECT_HOST (default "localhost")
    - UPSTOX_REDIRECT_PORT (default 8080)
    - UPSTOX_REDIRECT_PATH (default "/upstox_auth")
    
    Returns:
        An UpstoxConfig instance populated from the environment.
    
    Raises:
        ValueError: If either UPSTOX_CLIENT_ID or UPSTOX_CLIENT_SECRET is not set.
    """

    client_id = os.getenv("UPSTOX_CLIENT_ID")
    client_secret = os.getenv("UPSTOX_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("UPSTOX_CLIENT_ID and UPSTOX_CLIENT_SECRET must be set.")

    redirect_host = os.getenv("UPSTOX_REDIRECT_HOST", "localhost")
    redirect_port = int(os.getenv("UPSTOX_REDIRECT_PORT", "8080"))
    redirect_path = os.getenv("UPSTOX_REDIRECT_PATH", "/upstox_auth")
    return UpstoxConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_host=redirect_host,
        redirect_port=redirect_port,
        redirect_path=redirect_path,
    )


def load_database_config() -> DatabaseConfig:
    """
    Load TimescaleDB configuration from environment variables.
    
    Reads UPSTOX_PG_DSN (required), UPSTOX_PG_BATCH (optional, default 1000) and UPSTOX_PG_FLUSH_INTERVAL (optional, default 0.5) and returns a DatabaseConfig populated from those values.
    
    Returns:
        DatabaseConfig: Configuration with `dsn`, `batch_size`, and `flush_interval_seconds` set from the environment.
    
    Raises:
        ValueError: If UPSTOX_PG_DSN is not configured.
    """

    dsn = os.getenv("UPSTOX_PG_DSN")
    if not dsn:
        raise ValueError("UPSTOX_PG_DSN must be configured.")

    return DatabaseConfig(
        dsn=dsn,
        batch_size=int(os.getenv("UPSTOX_PG_BATCH", "1000")),
        flush_interval_seconds=float(os.getenv("UPSTOX_PG_FLUSH_INTERVAL", "0.5")),
    )


def load_redis_config() -> RedisConfig:
    """
    Load Redis cache configuration from environment variables.
    
    Reads UPSTOX_REDIS_URL (required) and UPSTOX_REDIS_TTL (optional, defaults to 10) and returns a RedisConfig with the resolved URL and TTL in seconds.
    
    Returns:
        RedisConfig: Configuration containing the cache URL and TTL in seconds.
    
    Raises:
        ValueError: If UPSTOX_REDIS_URL is not set.
    """

    url = os.getenv("UPSTOX_REDIS_URL")
    if not url:
        raise ValueError("UPSTOX_REDIS_URL must be set for cache usage.")
    return RedisConfig(url=url, ttl_seconds=int(os.getenv("UPSTOX_REDIS_TTL", "10")))


def load_smtp_config() -> SmtpConfig:
    """
    Load and validate SMTP configuration from environment variables.
    
    Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_SENDER and SMTP_RECIPIENTS, validates all are present, and returns an SmtpConfig with the parsed values.
    
    Returns:
        SmtpConfig: SMTP settings populated from the corresponding environment variables (port converted to int).
    
    Raises:
        ValueError: If any required SMTP environment variable is missing or empty.
    """

    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_SENDER")
    recipients = os.getenv("SMTP_RECIPIENTS")
    if not all([host, port, username, password, sender, recipients]):
        raise ValueError("SMTP configuration incomplete.")
    return SmtpConfig(
        host=host,
        port=int(port),
        username=username,
        password=password,
        sender=sender,
        recipients=recipients,
    )


def load_stream_config() -> StreamConfig:
    """
    Load streaming service configuration from environment.
    
    Returns:
        StreamConfig: Configuration with `access_token`, `instrument_file`, and `mode` populated from environment variables.
    
    Raises:
        ValueError: If `UPSTOX_ACCESS_TOKEN` is not set.
    """

    access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("UPSTOX_ACCESS_TOKEN must be provided for streaming service.")

    instrument_file = os.getenv(
        "UPSTOX_INSTRUMENT_FILE", "complete_data_formatted.json"
    )
    mode = os.getenv("UPSTOX_STREAM_MODE", "ltpc")
    return StreamConfig(
        access_token=access_token, instrument_file=instrument_file, mode=mode
    )
