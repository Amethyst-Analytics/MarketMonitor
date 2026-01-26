# Authentication Service

Handles OAuth 2.0 flow with Upstox API to obtain access tokens for market data access.

## Overview

The `auth_service` module provides:

- **OAuth Client**: Complete OAuth 2.0 flow implementation
- **CLI Tool**: Command-line interface for token acquisition
- **Local HTTP Server**: Captures authorization callback

## Components

### OAuthClient (`oauth_client.py`)

High-level orchestrator for the Upstox OAuth flow.

#### Key Methods

- `build_authorization_url()`: Constructs the authorization URL
- `_wait_for_auth_code()`: Runs local HTTP server to capture callback
- `_exchange_code_for_token()`: Exchanges code for access token
- `run_flow()`: Executes complete OAuth flow

#### Usage

```python
from src.auth_service.oauth_client import OAuthClient
from src.common.config import load_upstox_config

config = load_upstox_config()
client = OAuthClient(config)
token_payload = client.run_flow(timeout=180, open_browser=True)
print(token_payload['access_token'])
```

### CLI (`cli.py`)

Command-line interface for OAuth flow.

#### Commands

```bash
# Run OAuth flow with browser auto-open
python -m auth_service

# Print authorization URL without opening browser
python -m auth_service --no-browser

# Set custom timeout (default: 180 seconds)
python -m auth_service --timeout 300
```

#### Output

```json
{
  "access_token": "eyJ...",
  "expires_in": 86400,
  "token_type": "Bearer",
  "scope": "..."
}
```

## Configuration

Required environment variables:

```bash
UPSTOX_CLIENT_ID="your_client_id"
UPSTOX_CLIENT_SECRET="your_client_secret"
UPSTOX_REDIRECT_HOST="localhost"
UPSTOX_REDIRECT_PORT="8080"
UPSTOX_REDIRECT_PATH="/upstox_auth"
```

## Security Notes

- **HTTPS**: Always use HTTPS in production for redirect URLs
- **Token Storage**: Store access tokens securely (environment variables, secret manager)
- **Scope**: Request minimum necessary scopes
- **State**: Consider adding state parameter for CSRF protection

## Testing

```bash
# Run auth service tests
python -m pytest tests/test_auth_service.py -v
```

## Integration

The access token obtained from this service is used by:

- `stream_service`: For WebSocket authentication
- `catalog_service`: For API calls to fetch instrument data

## Error Handling

Common errors and solutions:

| Error             | Cause                | Solution                         |
| ----------------- | -------------------- | -------------------------------- |
| `TimeoutError`    | No callback received | Check firewall, increase timeout |
| `ApiException`    | Invalid credentials  | Verify client ID/secret          |
| `ConnectionError` | Network issues       | Check internet connectivity      |

## Troubleshooting

1. **Port already in use**: Change `UPSTOX_REDIRECT_PORT`
2. **Browser not opening**: Use `--no-browser` flag and manually visit URL
3. **Invalid redirect URI**: Ensure it matches Upstox app settings
4. **Token expired**: Re-run OAuth flow to obtain new token

## Development

### Adding New OAuth Providers

1. Create new client class in `oauth_client.py`
2. Implement required methods following the same interface
3. Add CLI options in `cli.py`
4. Add tests in `tests/test_auth_service.py`

### Local Testing

```bash
# Set test credentials
export UPSTOX_CLIENT_ID="test_id"
export UPSTOX_CLIENT_SECRET="test_secret"

# Run OAuth flow (will fail at token exchange)
python -m auth_service --no-browser
```
