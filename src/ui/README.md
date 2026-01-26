# UI Service

Provides a FastAPI backend and Streamlit frontend for MarketMonitor, offering real-time dashboards and API access to market data.

## Architecture

```
ui/
├─ backend/           # FastAPI REST API
│  ├─ api.py          # FastAPI application and endpoints
│  ├─ services.py     # Business logic layer
│  └─ __main__.py     # Backend server entrypoint
└─ frontend/          # Streamlit web application
   ├─ app.py          # Main Streamlit application
   └─ pages/          # Page modules
      ├─ auth.py       # Authentication status
      ├─ instruments.py # Instrument management
      └─ ticks.py      # Tick data viewer
```

## Backend (FastAPI)

### API Endpoints

#### Health Check

```http
GET /health
```

Response:

```json
{ "status": "ok" }
```

#### Authentication Status

```http
GET /auth/status
```

Response:

```json
{ "has_token": true }
```

#### Instruments

```http
GET /instruments/subscribed
```

Response:

```json
[
  {
    "isin": "INE002A01018",
    "instrument_key": "NSE_EQ|INE002A01018",
    "trading_symbol": "INFY",
    "tracking_status": true
  }
]
```

#### Bulk ISIN Operations

```http
POST /isin/bulk
Content-Type: application/json

{
  "isins": ["INE001", "INE002", "INE003"]
}
```

Response:

```json
{
  "added": ["INE001"],
  "removed": ["INE002"],
  "errors": ["INE003 - Invalid ISIN"]
}
```

#### Latest Prices

```http
GET /ticks/latest?isins=INE001,INE002
```

Response:

```json
{
  "INE001": {
    "price": 1500.25,
    "timestamp": "2025-01-01T12:00:00Z"
  },
  "INE002": null
}
```

#### Historical Ticks

```http
GET /ticks/history?isin=INE001&start=2025-01-01T00:00:00Z&end=2025-01-01T23:59:59Z
```

Response:

```json
[
  {
    "timestamp": "2025-01-01T12:00:00Z",
    "price": 1500.25,
    "volume": 1000
  }
]
```

### Service Layer (`services.py`)

Business logic functions:

```python
def get_auth_status() -> dict:
    """Return whether an access token is configured."""

def list_subscribed_instruments() -> List[dict]:
    """Return instruments with tracking_status=true."""

def get_latest_prices(isins: List[str]) -> dict:
    """Fetch latest prices from Redis for given ISINs."""

def get_tick_history(isin: str, start: str, end: str) -> List[dict]:
    """Return historical ticks for an ISIN between timestamps."""
```

### Running the Backend

```bash
# Start FastAPI server
python -m ui.backend

# Or with uvicorn directly
uvicorn ui.backend:app --host 0.0.0.0 --port 8000 --reload
```

### Configuration

Required environment variables:

```bash
UPSTOX_ACCESS_TOKEN="your_access_token"
UPSTOX_PG_DSN="postgresql://..."
UPSTOX_REDIS_URL="redis://..."
```

## Frontend (Streamlit)

### Pages

#### Authentication (`pages/auth.py`)

Displays OAuth authentication status and provides instructions.

Features:

- Token presence indicator
- Instructions for obtaining token
- Link to auth service

#### Instruments (`pages/instruments.py`)

Instrument management interface.

Features:

- Bulk ISIN upload via CSV
- Subscribed instruments list
- Manual ISIN add/remove

#### Ticks (`pages/ticks.py`)

Tick data visualization and analysis.

Features:

- ISIN selector
- Date range picker
- Latest price display
- Historical tick chart

### Main Application (`app.py`)

Multipage navigation hub:

```python
import streamlit as st

PAGES = {
    "Authentication": pages.auth,
    "Instruments": pages.instruments,
    "Ticks": pages.ticks,
}

def main():
    st.set_page_config(page_title="MarketMonitor", layout="wide")
    page = st.sidebar.selectbox("Select Page", list(PAGES.keys()))
    PAGES[page].show()
```

### Running the Frontend

```bash
# Start Streamlit app
streamlit run src/ui/frontend/app.py

# Or with custom port
streamlit run src/ui/frontend/app.py --server.port 8501
```

### Customization

#### Theming

```python
import streamlit as st

# Custom theme
st.set_page_config(
    page_title="MarketMonitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

#### Components

Create reusable components:

```python
def price_chart(data: pd.DataFrame):
    """Display price chart with proper formatting."""
    st.line_chart(data.set_index('timestamp'))

def instrument_selector():
    """Instrument selection widget."""
    return st.multiselect(
        "Select Instruments",
        options=get_instrument_list(),
        default=[]
    )
```

## Integration

### Backend-Frontend Communication

The frontend calls backend APIs:

```python
import requests

def get_auth_status():
    response = requests.get("http://localhost:8000/auth/status")
    return response.json()

def get_latest_prices(isins):
    params = {"isins": ",".join(isins)}
    response = requests.get("http://localhost:8000/ticks/latest", params=params)
    return response.json()
```

### Error Handling

Implement proper error handling in frontend:

```python
try:
    data = get_latest_prices(isins)
except requests.exceptions.ConnectionError:
    st.error("Cannot connect to backend API")
except Exception as e:
    st.error(f"Error fetching data: {e}")
```

## Performance Optimization

### Backend

- **Database Connection Pooling**: Use connection pools
- **Redis Caching**: Cache frequently accessed data
- **Pagination**: Implement pagination for large datasets
- **Async Endpoints**: Use async/await for I/O operations

### Frontend

- **Data Caching**: Use `@st.cache_data` for expensive operations
- **Lazy Loading**: Load data on-demand
- **Chart Optimization**: Limit data points for charts
- **Session State**: Use `st.session_state` for user preferences

## Security

### Backend Security

```python
from fastapi import HTTPException
from pydantic import BaseModel

class BulkIsinRequest(BaseModel):
    isins: List[str]

@app.post("/isin/bulk")
def bulk_isin(request: BulkIsinRequest):
    # Validate ISIN format
    for isin in request.isins:
        if not validate_isin(isin):
            raise HTTPException(status_code=400, detail=f"Invalid ISIN: {isin}")
    # Process request
```

### Frontend Security

- **Input Validation**: Validate all user inputs
- **XSS Prevention**: Use Streamlit's built-in protection
- **CSRF Protection**: Use session tokens for state changes

## Testing

### Backend Tests

```bash
# Run backend API tests
python -m pytest tests/test_ui_backend.py -v

# Test specific endpoint
python -m pytest tests/test_ui_backend.py::TestUIBackendAPI::test_health_endpoint -v
```

### Frontend Tests

Streamlit doesn't have built-in testing, but you can:

1. **Unit Test Components**: Test individual functions
2. **Integration Tests**: Test API calls
3. **E2E Tests**: Use Selenium or Playwright

```python
# Example component test
def test_isin_validation():
    assert validate_isin("INE002A01018") == True
    assert validate_isin("INVALID") == False
```

## Deployment

### Docker

Backend Dockerfile:

```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "ui.backend:app", "--host", "0.0.0.0", "--port", "8000"]
```

Frontend Dockerfile:

```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/
WORKDIR /app
EXPOSE 8501
CMD ["streamlit", "run", "src/ui/frontend/app.py", "--server.port=8501"]
```

### Kubernetes

Backend deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ui-backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ui-backend
  template:
    spec:
      containers:
        - name: ui-backend
          image: marketmonitor/ui-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: marketmonitor-secrets
```

Frontend deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ui-frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ui-frontend
  template:
    spec:
      containers:
        - name: ui-frontend
          image: marketmonitor/ui-frontend:latest
          ports:
            - containerPort: 8501
          env:
            - name: BACKEND_URL
              value: "http://ui-backend:8000"
```

## Monitoring

### Backend Metrics

- **Request Count**: Track API usage
- **Response Time**: Monitor performance
- **Error Rate**: Track failures
- **Active Users**: Monitor concurrent sessions

### Frontend Analytics

- **Page Views**: Track popular pages
- **User Actions**: Monitor feature usage
- **Error Events**: Track frontend errors
- **Performance**: Monitor load times

## Troubleshooting

### Common Issues

1. **Backend Not Responding**
   - Check if server is running
   - Verify port accessibility
   - Check logs for errors

2. **Frontend Not Loading**
   - Check Streamlit server status
   - Verify backend connectivity
   - Check browser console for errors

3. **Data Not Displaying**
   - Verify database connection
   - Check Redis cache status
   - Validate API responses

### Debug Mode

Enable debug logging:

```python
# Backend
import logging
logging.getLogger("ui.backend").setLevel(logging.DEBUG)

# Frontend
import streamlit as st
st.write(f"Debug: {st.session_state}")
```

## Development

### Adding New Pages

1. Create new page module in `pages/`
2. Implement `show()` function
3. Add to page navigation in `app.py`
4. Write tests

Example:

```python
# pages/analytics.py
import streamlit as st

def show():
    st.title("Analytics")
    # Analytics content here
```

### Adding New API Endpoints

1. Define Pydantic models for request/response
2. Implement endpoint in `api.py`
3. Add business logic in `services.py`
4. Write tests

Example:

```python
# New endpoint
@app.get("/analytics/summary")
def analytics_summary():
    return get_analytics_summary()
```
