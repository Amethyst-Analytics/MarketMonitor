# MarketMonitor

Production-grade market data streaming framework for Upstox with real-time ingestion, storage, and visualization.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (TimescaleDB) and Redis

### One-Click Setup

1. **Clone and install dependencies**

   ```bash
   git clone <repo-url>
   cd MarketMonitor
   python -m venv venv
   .\venv\Scripts\Activate  # Windows
   source venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your Upstox credentials and DB/Redis URLs
   ```

3. **Run provisioning and services**

   ```bash
   python run_market_monitor.py              # One‑time provisioning
   python run_market_monitor.py --services    # Start services
   # Or use platform scripts:
   # Linux/macOS: ./src/scripts/start-services.sh
   # Windows: .\src\scripts\start-services.ps1
   ```

4. **Access the UI**
   - Frontend: http://localhost:8501
   - API: http://localhost:8000

## 📋 Architecture

### Components

| Service           | Purpose                            | Tech                           |
| ----------------- | ---------------------------------- | ------------------------------ |
| `auth_service`    | OAuth 2.0 flow for Upstox          | FastAPI, HTTP Server           |
| `stream_service`  | Real-time market data ingestion    | WebSockets, TimescaleDB, Redis |
| `catalog_service` | Instrument and MTF synchronization | HTTP, Cron                     |
| `ui`              | Backend API + Streamlit frontend   | FastAPI, Streamlit             |

### Data Flow

1. **OAuth** → Access token stored in `.env`
2. **Catalog** → Instruments loaded into PostgreSQL
3. **Streamer** → WebSocket → Batching → TimescaleDB + Redis cache
4. **UI** → FastAPI → Streamlit dashboards

### Design Patterns

- **Domain-Driven Design**: Layered architecture (Domain, Application, Infrastructure, Presentation)
- **Strategy Pattern**: Service launchers, storage backends
- **Factory Pattern**: Manager and service creation
- **Command Pattern**: Setup steps
- **Repository Pattern**: Data access abstraction

## 🛠️ Development

### Project Structure

```
MarketMonitor/
├─ src/
│  ├─ auth_service/          # OAuth client and CLI
│  ├─ stream_service/        # Ingestion, repositories, streaming client
│  ├─ catalog_service/       # Instrument/MTF loaders
│  ├─ ui/                    # FastAPI backend + Streamlit frontend
│  ├─ common/                # Config, logging, exceptions, utils
│  ├─ scripts/               # Service launcher, platform scripts
│  └─ setup.py               # OOP onboarding orchestrator
├─ deployments/
│  ├─ docker-compose/        # Local Docker setup
│  └─ k8s/                   # Kubernetes manifests
├─ migrations/               # Database schema
├─ tests/                    # Test suite
├─ .env.example              # Environment template
├─ requirements.txt          # Dependencies
├─ pyproject.toml           # Project metadata
└─ run_market_monitor.py    # Root entrypoint
```

### Code Quality

- **Absolute imports** from project root
- **Type hints** throughout
- **Structured logging** with `src.common.logging`
- **Custom exceptions** in `src.common.exceptions`
- **Configuration validation** via `src.common.validator`
- **Comprehensive tests** with pytest

### Running Tests

```bash
# Set required environment variables
export UPSTOX_PG_DSN="postgresql://postgres:postgres@localhost:5432/market_data"
export UPSTOX_REDIS_URL="redis://localhost:6379/0"

# Run all tests
python -m pytest tests -v --tb=short

# Run specific test file
python -m pytest tests/test_auth_service.py -v
```

### Linting & Formatting

```bash
# Lint
ruff check src tests

# Format
black src tests

# Type check
mypy src
```

## 🐳 Deployment

### Local Docker

```bash
cd deployments/docker-compose
docker compose up -d
```

### Kubernetes

```bash
cd deployments/k8s
kubectl apply -f .
# Or use kustomize:
kubectl apply -k .
```

### Environment Variables

| Variable                   | Required? | Description                                 |
| -------------------------- | --------- | ------------------------------------------- |
| `UPSTOX_CLIENT_ID`         | ✅        | Upstox OAuth client ID                      |
| `UPSTOX_CLIENT_SECRET`     | ✅        | Upstox OAuth client secret                  |
| `UPSTOX_ACCESS_TOKEN`      | ✅        | OAuth access token (auto-populated)         |
| `UPSTOX_REDIRECT_HOST`     | ✅        | OAuth redirect host (default: localhost)    |
| `UPSTOX_REDIRECT_PORT`     | ✅        | OAuth redirect port (default: 8080)         |
| `UPSTOX_REDIRECT_PATH`     | ✅        | OAuth redirect path (default: /upstox_auth) |
| `UPSTOX_INSTRUMENT_FILE`   | ✅        | Path to instrument catalog                  |
| `UPSTOX_STREAM_MODE`       | ✅        | Stream mode (ltpc, ltp)                     |
| `UPSTOX_PG_DSN`            | ✅        | PostgreSQL connection string                |
| `UPSTOX_PG_BATCH`          | ✅        | Batch size for DB inserts (default: 1000)   |
| `UPSTOX_PG_FLUSH_INTERVAL` | ✅        | Flush interval seconds (default: 0.5)       |
| `UPSTOX_REDIS_URL`         | ✅        | Redis connection URL                        |
| `UPSTOX_REDIS_TTL`         | ✅        | Redis TTL seconds (default: 10)             |
| `SMTP_HOST`                | ⚪        | SMTP server for alerts                      |
| `SMTP_PORT`                | ⚪        | SMTP port (default: 587)                    |
| `SMTP_USER`                | ⚪        | SMTP username                               |
| `SMTP_PASS`                | ⚪        | SMTP password                               |
| `SMTP_SENDER`              | ⚪        | Alert sender email                          |
| `SMTP_RECIPIENTS`          | ⚪        | Alert recipient emails                      |

### Secret Management

#### Local Development

```bash
cp .env.example .env
# Edit .env with your values
```

#### Docker

```bash
docker compose --env-file .env up -d
```

#### Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: marketmonitor-secrets
type: Opaque
stringData:
  UPSTOX_CLIENT_ID: "..."
  UPSTOX_CLIENT_SECRET: "..."
  UPSTOX_ACCESS_TOKEN: "..."
  UPSTOX_PG_DSN: "postgresql://..."
  UPSTOX_REDIS_URL: "redis://..."
```

## 📊 Database Schema

### Core Tables

- **instruments**: Master instrument list with tracking status
- **ticks**: Hypertable for time-series tick data
- **mtf_securities**: Zerodha MTF approved securities
- **tracking_overrides**: Manual ISIN inclusions/exclusions

### Schema Migration

```bash
# Apply initial schema (handled automatically by setup.py)
psql -U postgres -d market_data -f migrations/001_initial.sql
```

## 🔧 Operations

### Service Management

```bash
# Start all services
python run_market_monitor.py --services

# Start individual services
python -m stream_service --catalog complete_data_formatted.json
python -m ui.backend
streamlit run src/ui/frontend/app.py

# Stop services
./src/scripts/stop-services.sh  # Linux/macOS
.\src\scripts\stop-services.ps1  # Windows
```

### Health Checks

- **API Health**: `GET /health`
- **Database**: Verify connection via `src/common/validator.py`
- **Redis**: Verify connection via `src/common/validator.py`

### Monitoring

- **Logs**: Service logs in project root (`streamer.log`, `ui-backend.log`, `ui-frontend.log`)
- **Metrics**: Add Prometheus endpoints as needed
- **Alerting**: SMTP alerts for critical errors (configurable)

## 🧪 Testing

### Test Categories

- **Unit Tests**: Individual components (repositories, services)
- **Integration Tests**: End-to-end workflows
- **API Tests**: FastAPI endpoints

### Test Environment Setup

```bash
# Start test dependencies
docker compose -f deployments/docker-compose/docker-compose.yml up -d

# Set test environment variables
export UPSTOX_CLIENT_ID="test"
export UPSTOX_CLIENT_SECRET="test"
export UPSTOX_ACCESS_TOKEN="test"
export UPSTOX_PG_DSN="postgresql://postgres:postgres@localhost:5432/market_data"
export UPSTOX_REDIS_URL="redis://localhost:6379/0"

# Run tests
python -m pytest tests -v --tb=short
```

## 📚 Module Documentation

- [auth_service](src/auth_service/README.md) - OAuth client and CLI
- [stream_service](src/stream_service/README.md) - Market data ingestion
- [catalog_service](src/catalog_service/README.md) - Instrument catalog management
- [ui](src/ui/README.md) - Backend API and frontend
- [common](src/common/README.md) - Shared utilities and configuration
- [scripts](src/scripts/README.md) - Service launcher and platform scripts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run linting and tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- [Upstox API Documentation](https://upstox.com/developer/api-documentation/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
