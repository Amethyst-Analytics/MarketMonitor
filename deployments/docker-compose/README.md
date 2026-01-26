# Docker Compose

Local development environment for MarketMonitor using Docker Compose.

## Overview

This setup provides:

- **TimescaleDB**: PostgreSQL with TimescaleDB extension
- **Redis**: In-memory data store for caching
- **Persistent Data**: Data persists across container restarts
- **Easy Setup**: Single command to start all services

## Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose
- At least 2GB available RAM

### Starting Services

```bash
cd deployments/docker-compose
docker compose up -d
```

This will:

- Download required Docker images
- Start TimescaleDB on port 5432
- Start Redis on port 6379
- Create persistent volumes for data

### Stopping Services

```bash
docker compose down
```

### Resetting Data

```bash
docker compose down -v
docker compose up -d
```

## Services

### TimescaleDB

- **Image**: `timescale/timescaledb:latest-pg15`
- **Port**: 5432
- **Database**: `market_data`
- **User**: `postgres`
- **Password**: `admin123` (configurable)

#### Connection String

```
postgresql://postgres:admin123@localhost:5432/market_data
```

#### Accessing Database

```bash
# Connect using psql
docker compose exec timescaledb psql -U postgres -d market_data

# Connect using any PostgreSQL client
psql -h localhost -p 5432 -U postgres -d market_data
```

#### Schema Management

```bash
# Apply initial schema
docker compose exec timescaledb psql -U postgres -d market_data -f /docker-entrypoint-initdb.d/001_initial.sql
```

### Redis

- **Image**: `redis:7-alpine`
- **Port**: 6379
- **Password**: None (default)

#### Connection String

```
redis://localhost:6379/0
```

#### Accessing Redis

```bash
# Connect using redis-cli
docker compose exec redis redis-cli

# Connect using any Redis client
redis-cli -h localhost -p 6379
```

## Configuration

### Environment Variables

Create a `.env` file in the same directory:

```bash
# PostgreSQL Configuration
POSTGRES_PASSWORD=admin123
POSTGRES_DB=market_data
POSTGRES_USER=postgres

# Redis Configuration (optional)
REDIS_PASSWORD=
```

### Custom Configuration

#### Custom PostgreSQL Settings

Create `custom-postgres.conf`:

```ini
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB

# Connection settings
max_connections = 200
shared_preload_libraries = 'timescaledb'

# Logging
log_statement = 'all'
log_min_duration_statement = 1000
```

Update `docker-compose.yml`:

```yaml
services:
  timescaledb:
    volumes:
      - ./custom-postgres.conf:/etc/postgresql/postgresql.conf
```

#### Custom Redis Configuration

Create `redis.conf`:

```ini
# Memory settings
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
```

Update `docker-compose.yml`:

```yaml
services:
  redis:
    volumes:
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
```

## Data Persistence

### Volumes

- `timescaledb_data`: PostgreSQL data directory
- `redis_data`: Redis data directory

### Backup Data

```bash
# Backup PostgreSQL
docker compose exec timescaledb pg_dump -U postgres market_data > backup.sql

# Backup Redis
docker compose exec redis redis-cli BGSAVE
docker compose cp redis:/data/dump.rdb ./redis-backup.rdb
```

### Restore Data

```bash
# Restore PostgreSQL
docker compose exec -i timescaledb psql -U postgres market_data < backup.sql

# Restore Redis
docker compose cp ./redis-backup.rdb redis:/data/dump.rdb
docker compose restart redis
```

## Development Workflow

### Database Schema Changes

1. Create migration file in `migrations/`
2. Apply migration:
   ```bash
   docker compose exec timescaledb psql -U postgres -d market_data -f migrations/002_new_table.sql
   ```
3. Update documentation

### Testing with Local Data

```bash
# Load sample data
docker compose exec timescaledb psql -U postgres -d market_data -c "
INSERT INTO instruments (instrument_key, isin, exchange, trading_symbol) VALUES
('NSE_EQ|INE001', 'INE001', 'NSE', 'TEST');
"
```

### Connecting from Applications

#### Python

```python
import psycopg2
import redis

# PostgreSQL
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='market_data',
    user='postgres',
    password='admin123'
)

# Redis
r = redis.Redis(host='localhost', port=6379, db=0)
```

#### Node.js

```javascript
const { Client } = require("pg");
const redis = require("redis");

// PostgreSQL
const client = new Client({
  host: "localhost",
  port: 5432,
  database: "market_data",
  user: "postgres",
  password: "admin123",
});

// Redis
const redisClient = redis.createClient({
  host: "localhost",
  port: 6379,
});
```

## Monitoring

### Checking Service Status

```bash
# Check all services
docker compose ps

# Check logs
docker compose logs -f timescaledb
docker compose logs -f redis

# Check resource usage
docker stats
```

### Health Checks

#### PostgreSQL Health

```bash
# Check if PostgreSQL is ready
docker compose exec timescaledb pg_isready -U postgres

# Check database size
docker compose exec timescaledb psql -U postgres -d market_data -c "
SELECT pg_size_pretty(pg_database_size('market_data'));
"
```

#### Redis Health

```bash
# Check Redis status
docker compose exec redis redis-cli ping

# Check memory usage
docker compose exec redis redis-cli info memory
```

## Performance Tuning

### PostgreSQL Optimization

```yaml
services:
  timescaledb:
    environment:
      - POSTGRES_SHARED_PRELOAD_LIBRARIES=timescaledb
      - POSTGRES_MAX_CONNECTIONS=200
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Redis Optimization

```yaml
services:
  redis:
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## Troubleshooting

### Common Issues

#### Port Conflicts

If ports 5432 or 6379 are already in use:

```bash
# Stop conflicting services
sudo systemctl stop postgresql
sudo systemctl stop redis

# Or change ports in docker-compose.yml
```

#### Permission Issues

```bash
# Fix Docker permissions
sudo chown -R $USER:$USER /var/lib/docker
```

#### Memory Issues

```bash
# Check Docker memory usage
docker system df
docker system prune
```

#### Connection Issues

```bash
# Check network
docker network ls
docker network inspect docker-compose_default

# Restart services
docker compose restart
```

### Debug Mode

Enable debug logging:

```yaml
services:
  timescaledb:
    environment:
      - POSTGRES_LOG_STATEMENT=all
      - POSTGRES_LOG_MIN_DURATION_STATEMENT=100
```

## Advanced Usage

### Custom Networks

```yaml
networks:
  marketmonitor:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Multiple Environments

Create separate compose files:

- `docker-compose.yml` (base)
- `docker-compose.override.yml` (development)
- `docker-compose.prod.yml` (production)

### Integration Tests

```bash
# Run tests against local services
TEST_DATABASE_URL=postgresql://postgres:admin123@localhost:5432/market_data \
TEST_REDIS_URL=redis://localhost:6379/0 \
pytest tests/
```

## Security

### Network Security

- Services communicate only within Docker network
- No external access to database ports
- Use strong passwords

### Data Security

- Store sensitive data in environment variables
- Use `.env` file (add to `.gitignore`)
- Regularly rotate passwords

### Access Control

```bash
# Limit Docker socket access
sudo groupadd docker
sudo usermod -aG docker $USER
```

## Production Considerations

This Docker Compose setup is intended for development and testing. For production:

1. Use external managed database services
2. Implement proper backup strategies
3. Set up monitoring and alerting
4. Use Kubernetes or orchestration platform
5. Implement security best practices

## Migration to Production

### Export Data

```bash
# Export PostgreSQL data
docker compose exec timescaledb pg_dump -U postgres market_data > production-data.sql

# Export Redis data
docker compose exec redis redis-cli --rdb /data/dump.rdb
```

### Import to Production

```bash
# Import to production database
psql -h prod-host -U prod-user -d market_data < production-data.sql

# Import to production Redis
redis-cli -h prod-host --pipe < dump.rdb
```

## Support

### Getting Help

1. Check Docker logs: `docker compose logs`
2. Verify configuration: `docker compose config`
3. Check resource usage: `docker stats`
4. Restart services: `docker compose restart`

### Common Commands

```bash
# View compose configuration
docker compose config

# Rebuild containers
docker compose build --no-cache

# Force recreate
docker compose up -d --force-recreate

# Remove all data
docker compose down -v
```

### Documentation

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Redis Documentation](https://redis.io/documentation)
