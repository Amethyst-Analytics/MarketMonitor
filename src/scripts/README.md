# Scripts

Service management and deployment scripts for MarketMonitor.

## Overview

The `scripts` directory contains:

- **Service Launcher**: Python module using Strategy pattern for service management
- **Platform Scripts**: Shell/PowerShell scripts for starting/stopping services
- **Service Definitions**: Configurations for different services

## Components

### Service Launcher (`service_launcher.py`)

Python module that implements the Strategy pattern for launching services with proper logging and process management.

#### Architecture

```python
@dataclass(frozen=True)
class ServiceConfig:
    """Configuration for a background service."""
    cmd: List[str]
    logfile: str
    name: str

class ServiceLauncher(ABC):
    """Abstract strategy for launching services."""

    @abstractmethod
    def launch(self, services: List[ServiceConfig]) -> None:
        """Launch the given services."""

class BackgroundServiceLauncher(ServiceLauncher):
    """Launches services in background with log files."""

    def launch(self, services: List[ServiceConfig]) -> None:
        # Implementation with process management
```

#### Service Factory

```python
class ServiceFactory:
    """Factory to create service configurations."""

    @staticmethod
    def create_marketmonitor_services() -> List[ServiceConfig]:
        catalog_path = Path("../../complete_data_formatted.json")
        return [
            ServiceConfig(
                cmd=[sys.executable, "-m", "stream_service", "--catalog", str(catalog_path)],
                logfile="../../streamer.log",
                name="streamer",
            ),
            ServiceConfig(
                cmd=[sys.executable, "-m", "ui.backend"],
                logfile="../../ui-backend.log",
                name="ui-backend",
            ),
            ServiceConfig(
                cmd=["streamlit", "run", "src/ui/frontend/app.py"],
                logfile="../../ui-frontend.log",
                name="ui-frontend",
            ),
        ]
```

#### Usage

```python
from src.scripts.service_launcher import BackgroundServiceLauncher, ServiceFactory

launcher = BackgroundServiceLauncher()
services = ServiceFactory.create_marketmonitor_services()
launcher.launch(services)
```

### Platform Scripts

#### Linux/macOS (`start-services.sh`)

```bash
#!/bin/bash
# Start MarketMonitor services

cd "$(dirname "$0")"
python -m service_launcher
```

#### Windows (`start-services.ps1`)

```powershell
# Start MarketMonitor services

Set-Location $PSScriptRoot
python -m service_launcher
```

#### Linux/macOS (`stop-services.sh`)

```bash
#!/bin/bash
# Stop MarketMonitor services

pkill -f "stream_service"
pkill -f "ui.backend"
pkill -f "streamlit"
echo "Services stopped."
```

#### Windows (`stop-services.ps1`)

```powershell
# Stop MarketMonitor services

Get-Process | Where-Object {$_.ProcessName -like "*stream_service*" -or $_.ProcessName -like "*ui.backend*" -or $_.CommandLine -like "*streamlit*"} | Stop-Process -Force
Write-Host "Services stopped."
```

## Service Configurations

### Streamer Service

- **Command**: `python -m stream_service --catalog complete_data_formatted.json`
- **Log File**: `streamer.log`
- **Purpose**: Real-time market data ingestion

### UI Backend Service

- **Command**: `python -m ui.backend`
- **Log File**: `ui-backend.log`
- **Purpose**: FastAPI REST API server

### UI Frontend Service

- **Command**: `streamlit run src/ui/frontend/app.py`
- **Log File**: `ui-frontend.log`
- **Purpose**: Streamlit web application

## Usage

### Starting Services

#### Method 1: Using Python Module

```bash
cd src/scripts
python -m service_launcher
```

#### Method 2: Using Platform Scripts

```bash
# Linux/macOS
./src/scripts/start-services.sh

# Windows
.\src\scripts\start-services.ps1
```

#### Method 3: From Project Root

```bash
python run_market_monitor.py --services
```

### Stopping Services

#### Method 1: Using Platform Scripts

```bash
# Linux/macOS
./src/scripts/stop-services.sh

# Windows
.\src\scripts\stop-services.ps1
```

#### Method 2: Manual

```bash
# Find and kill processes
ps aux | grep stream_service
kill -9 <PID>

# Or use pkill
pkill -f stream_service
pkill -f ui.backend
pkill -f streamlit
```

## Service Management

### Process Monitoring

```bash
# Check if services are running
ps aux | grep -E "(stream_service|ui.backend|streamlit)"

# Check log files
tail -f streamer.log
tail -f ui-backend.log
tail -f ui-frontend.log
```

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:8501/_stcore/health
```

### Service Dependencies

1. **Infrastructure**: PostgreSQL and Redis must be running
2. **Configuration**: Environment variables must be set
3. **Instrument Catalog**: Must be available for streamer

## Error Handling

### Common Issues

1. **Port Already in Use**
   - Check if another service is using the port
   - Kill conflicting processes
   - Change port in configuration

2. **Permission Denied**
   - Check file permissions for log files
   - Ensure Python has execute permissions
   - Run with appropriate user

3. **Module Not Found**
   - Ensure Python path includes `src` directory
   - Check virtual environment activation
   - Verify requirements are installed

### Debug Mode

Enable debug logging:

```bash
export DEBUG=1
python -m service_launcher
```

## Customization

### Adding New Services

1. Add service configuration to `ServiceFactory`
2. Create service-specific launcher if needed
3. Update platform scripts
4. Add documentation

Example:

```python
@staticmethod
def create_marketmonitor_services() -> List[ServiceConfig]:
    services = [
        # Existing services...
        ServiceConfig(
            cmd=[sys.executable, "-m", "new_service"],
            logfile="../../new-service.log",
            name="new-service",
        ),
    ]
    return services
```

### Custom Launch Strategies

Implement custom launcher:

```python
class DockerServiceLauncher(ServiceLauncher):
    """Launch services in Docker containers."""

    def launch(self, services: List[ServiceConfig]) -> None:
        for service in services:
            # Docker launch logic
            pass
```

### Environment-Specific Configurations

```python
class ServiceFactory:
    @staticmethod
    def create_services(env: str = "dev") -> List[ServiceConfig]:
        if env == "dev":
            return create_development_services()
        elif env == "prod":
            return create_production_services()
        else:
            return create_marketmonitor_services()
```

## Deployment

### Docker Integration

```dockerfile
FROM python:3.11-slim
COPY src/ /app/src/
WORKDIR /app/src/scripts
CMD ["python", "-m", "service_launcher"]
```

### Kubernetes Integration

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: start-services
spec:
  template:
    spec:
      containers:
        - name: service-launcher
          image: marketmonitor/service-launcher:latest
          command: ["python", "-m", "service_launcher"]
          envFrom:
            - secretRef:
                name: marketmonitor-secrets
```

## Monitoring

### Service Status

```bash
# Check service status
python -c "
from src.scripts.service_launcher import ServiceFactory
services = ServiceFactory.create_marketmonitor_services()
for service in services:
    print(f'{service.name}: {service.cmd}')
"
```

### Log Analysis

```bash
# Count errors in logs
grep -c "ERROR" *.log

# Show recent errors
tail -n 100 streamer.log | grep "ERROR"

# Monitor logs in real-time
tail -f streamer.log | grep -E "(ERROR|WARN)"
```

## Security

### Process Permissions

- Run services with minimal privileges
- Use dedicated user for service execution
- Restrict file system access

### Log Security

- Ensure log files have appropriate permissions
- Rotate logs regularly
- Avoid logging sensitive information

## Best Practices

### Service Management

- **Idempotent**: Scripts should handle multiple runs gracefully
- **Error Recovery**: Implement retry logic for transient failures
- **Resource Limits**: Set appropriate memory and CPU limits
- **Graceful Shutdown**: Handle signals properly

### Logging

- **Structured**: Use consistent log format
- **Rotation**: Implement log rotation
- **Levels**: Use appropriate log levels
- **Security**: Avoid logging sensitive data

### Deployment

- **Environment-Specific**: Different configs for dev/prod
- **Health Checks**: Implement health check endpoints
- **Monitoring**: Add metrics and alerting
- **Rollback**: Plan for quick rollback

## Troubleshooting

### Service Won't Start

1. Check environment variables
2. Verify dependencies are installed
3. Check log files for errors
4. Ensure ports are available

### Service Crashes

1. Check log files for error messages
2. Verify configuration is correct
3. Check resource usage
4. Validate input data

### Performance Issues

1. Monitor resource usage
2. Check for memory leaks
3. Optimize database queries
4. Consider scaling options

## Development

### Testing Service Launcher

```python
import pytest
from src.scripts.service_launcher import ServiceFactory, BackgroundServiceLauncher

def test_service_factory():
    services = ServiceFactory.create_marketmonitor_services()
    assert len(services) == 3
    assert services[0].name == "streamer"

def test_background_launcher():
    launcher = BackgroundServiceLauncher()
    # Test with mock services
    pass
```

### Local Development

```bash
# Run service launcher in debug mode
python -m service_launcher

# Test individual service
python -m stream_service --catalog test_catalog.json

# Check service configuration
python -c "from src.scripts.service_launcher import ServiceFactory; print(ServiceFactory.create_marketmonitor_services())"
```

### Adding Tests

1. Create test file in `tests/`
2. Mock external dependencies
3. Test error conditions
4. Verify service configurations

## Maintenance

### Regular Tasks

- **Log Rotation**: Set up log rotation
- **Service Updates**: Update service configurations
- **Security Patches**: Apply security updates
- **Performance Tuning**: Optimize service performance

### Monitoring

- **Service Uptime**: Monitor service availability
- **Resource Usage**: Track CPU, memory, disk usage
- **Error Rates**: Monitor error frequency
- **Performance Metrics**: Track response times

### Documentation

- **Keep Updated**: Update documentation with changes
- **Examples**: Provide usage examples
- **Troubleshooting**: Maintain troubleshooting guide
- **API Docs**: Keep API documentation current
