# Docker

Container build configurations and utilities for MarketMonitor services.

## Overview

This directory contains:

- **Dockerfiles**: Multi-stage build configurations for each service
- **Build Scripts**: Cross-platform build automation
- **Optimization**: Production-ready container images

## Images Built

| Service         | Dockerfile                   | Tag                             | Purpose               |
| --------------- | ---------------------------- | ------------------------------- | --------------------- |
| Streamer        | `streamer.Dockerfile`        | `marketmonitor/streamer`        | Market data ingestion |
| UI Backend      | `ui-backend.Dockerfile`      | `marketmonitor/ui-backend`      | FastAPI REST API      |
| UI Frontend     | `ui-frontend.Dockerfile`     | `marketmonitor/ui-frontend`     | Streamlit web app     |
| Catalog Service | `catalog-service.Dockerfile` | `marketmonitor/catalog-service` | Instrument sync       |

## Quick Start

### Build All Images

#### Linux/macOS

```bash
cd deployments/docker
chmod +x build.sh
./build.sh
```

#### Windows

```powershell
cd deployments\docker
.\build.ps1
```

### Build Individual Images

```bash
# Build streamer image
docker build -f streamer.Dockerfile -t marketmonitor/streamer .

# Build UI backend
docker build -f ui-backend.Dockerfile -t marketmonitor/ui-backend .

# Build UI frontend
docker build -f ui-frontend.Dockerfile -t marketmonitor/ui-frontend .

# Build catalog service
docker build -f catalog-service.Dockerfile -t marketmonitor/catalog-service .
```

## Dockerfiles

### Multi-Stage Build Pattern

All Dockerfiles use multi-stage builds:

#### Stage 1: Build

- Install build dependencies
- Copy source code
- Install application dependencies

#### Stage 2: Runtime

- Copy only necessary files
- Set up runtime environment
- Optimize image size

### Streamer Dockerfile

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ /app/src/
EXPOSE 8000
CMD ["python", "-m", "stream_service"]
```

### UI Backend Dockerfile

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ /app/src/
EXPOSE 8000
CMD ["uvicorn", "ui.backend:app", "--host", "0.0.0.0", "--port", "8000"]
```

### UI Frontend Dockerfile

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ /app/src/
EXPOSE 8501
CMD ["streamlit", "run", "src/ui/frontend/app.py", "--server.port=8501"]
```

### Catalog Service Dockerfile

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ /app/src/
CMD ["python", "-m", "catalog_service"]
```

## Build Scripts

### Linux/macOS (`build.sh`)

```bash
#!/bin/bash
set -e

# Configuration
REGISTRY=${REGISTRY:-"marketmonitor"}
TAG=${TAG:-"latest"}
PUSH=${PUSH:-false}

# Build images
echo "Building Docker images..."

docker build -f streamer.Dockerfile -t ${REGISTRY}/streamer:${TAG} .
docker build -f ui-backend.Dockerfile -t ${REGISTRY}/ui-backend:${TAG} .
docker build -f ui-frontend.Dockerfile -t ${REGISTRY}/ui-frontend:${TAG} .
docker build -f catalog-service.Dockerfile -t ${REGISTRY}/catalog-service:${TAG} .

echo "Build completed successfully!"

# Push to registry if requested
if [ "$PUSH" = true ]; then
    echo "Pushing images to registry..."
    docker push ${REGISTRY}/streamer:${TAG}
    docker push ${REGISTRY}/ui-backend:${TAG}
    docker push ${REGISTRY}/ui-frontend:${TAG}
    docker push ${REGISTRY}/catalog-service:${TAG}
    echo "Push completed successfully!"
fi
```

### Windows (`build.ps1`)

```powershell
# Configuration
$Registry = if ($env:REGISTRY) { $env:REGISTRY } else { "marketmonitor" }
$Tag = if ($env:TAG) { $env:TAG } else { "latest" }
$Push = if ($env:PUSH) { [bool]$env:PUSH } else { $false }

Write-Host "Building Docker images..." -ForegroundColor Green

# Build images
docker build -f streamer.Dockerfile -t "${Registry}/streamer:${Tag}" .
docker build -f ui-backend.Dockerfile -t "${Registry}/ui-backend:${Tag}" .
docker build -f ui-frontend.Dockerfile -t "${Registry}/ui-frontend:${Tag}" .
docker build -f catalog-service.Dockerfile -t "${Registry}/catalog-service:${Tag}" .

Write-Host "Build completed successfully!" -ForegroundColor Green

# Push to registry if requested
if ($Push) {
    Write-Host "Pushing images to registry..." -ForegroundColor Yellow
    docker push "${Registry}/streamer:${Tag}"
    docker push "${Registry}/ui-backend:${Tag}"
    docker push "${Registry}/ui-frontend:${Tag}"
    docker push "${Registry}/catalog-service:${Tag}"
    Write-Host "Push completed successfully!" -ForegroundColor Green
}
```

## Configuration

### Environment Variables

Build scripts support these environment variables:

| Variable   | Description             | Default         |
| ---------- | ----------------------- | --------------- |
| `REGISTRY` | Docker registry URL     | `marketmonitor` |
| `TAG`      | Image tag               | `latest`        |
| `PUSH`     | Push images after build | `false`         |

### Custom Registry

```bash
# Build with custom registry
REGISTRY=myregistry.com/marketmonitor TAG=v1.0.0 ./build.sh

# Build and push
REGISTRY=myregistry.com/marketmonitor TAG=v1.0.0 PUSH=true ./build.sh
```

## Optimization

### Image Size Reduction

Multi-stage builds reduce image size by:

- Not including build dependencies in runtime
- Copying only necessary files
- Using slim base images

### Security

- Use non-root user where possible
- Scan images for vulnerabilities
- Use specific image tags
- Regular security updates

### Performance

- Use .dockerignore to exclude unnecessary files
- Optimize layer ordering
- Minimize number of layers

## .dockerignore

Create `.dockerignore` in project root:

```
# Python
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
.tox/
.venv/
venv/
env/

# Git
.git
.gitignore

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Documentation
docs/
*.md
```

## Security Scanning

### Trivy

```bash
# Scan for vulnerabilities
trivy image marketmonitor/streamer:latest
trivy image marketmonitor/ui-backend:latest
trivy image marketmonitor/ui-frontend:latest
trivy image marketmonitor/catalog-service:latest
```

### Grype

```bash
# Scan for vulnerabilities
grype marketmonitor/streamer:latest
grype marketmonitor/ui-backend:latest
grype marketmonitor/ui-frontend:latest
grype marketmonitor/catalog-service:latest
```

## Testing

### Local Testing

```bash
# Test image locally
docker run --rm -it marketmonitor/streamer:latest python --version

# Test with environment variables
docker run --rm -it \
  -e UPSTOX_ACCESS_TOKEN=test \
  marketmonitor/streamer:latest \
  python -c "import os; print('Token:', os.getenv('UPSTOX_ACCESS_TOKEN'))"
```

### Integration Testing

```bash
# Run integration tests in container
docker run --rm -it \
  -v $(pwd)/tests:/app/tests \
  -v $(pwd)/src:/app/src \
  marketmonitor/streamer:latest \
  python -m pytest tests/
```

## Deployment

### Local Development

```bash
# Run services with Docker Compose
docker compose up -d

# View logs
docker compose logs -f streamer
```

### Production

```bash
# Pull images
docker pull marketmonitor/streamer:latest
docker pull marketmonitor/ui-backend:latest
docker pull marketmonitor/ui-frontend:latest
docker pull marketmonitor/catalog-service:latest

# Run with Kubernetes
kubectl apply -f k8s/
```

## Version Management

### Semantic Versioning

Use semantic versioning for image tags:

- `1.0.0` - Major release
- `1.1.0` - Minor release
- `1.1.1` - Patch release

### Tagging Strategy

```bash
# Tag latest version
docker tag marketmonitor/streamer:v1.0.0 marketmonitor/streamer:latest

# Tag with build number
docker tag marketmonitor/streamer:v1.0.0 marketmonitor/streamer:1.0.0-build.42
```

## Multi-Architecture Builds

### ARM64 Support

```dockerfile
# Build for ARM64
FROM --platform=linux/arm64 python:3.11-slim
```

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 -t marketmonitor/streamer:latest .
```

### Buildx Configuration

```bash
# Create buildx builder
docker buildx create --name mybuilder --use

# Use builder for builds
docker buildx build --builder mybuilder -t marketmonitor/streamer:latest .
```

## Customization

### Adding New Service

1. Create new Dockerfile
2. Add to build script
3. Update documentation

Example:

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ /app/src/
CMD ["python", "-m", "new_service"]
```

### Custom Base Images

```dockerfile
FROM your-custom-python:3.11
WORKDIR /app
COPY src/ /app/src/
CMD ["python", "-m", "stream_service"]
```

### Runtime Configuration

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ /app/src/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Add non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

CMD ["python", "-m", "stream_service"]
```

## Best Practices

### Image Security

- Use specific base image tags
- Scan for vulnerabilities
- Use non-root users
- Minimize attack surface

### Performance

- Use .dockerignore
- Optimize layer caching
- Use multi-stage builds
- Minimize image size

### Maintainability

- Use semantic versioning
- Document build process
- Automate builds
- Test images thoroughly

### Reliability

- Use health checks
- Implement graceful shutdown
- Handle signals properly
- Log important events

## Troubleshooting

### Build Issues

```bash
# Check build logs
docker build -f streamer.Dockerfile --no-cache

# Debug with interactive shell
docker run -it --entrypoint /bin/bash marketmonitor/streamer:latest
```

### Runtime Issues

```bash
# Check container logs
docker logs <container-id>

# Debug with interactive shell
docker exec -it <container-id> /bin/bash

# Check environment variables
docker inspect <container-id> | grep Env
```

### Network Issues

```bash
# Test connectivity
docker run --rm -it --network host marketmonitor/streamer:latest curl http://localhost:8000/health

# Check network configuration
docker network ls
docker network inspect bridge
```

## Support

### Getting Help

1. Check Docker documentation
2. Review build logs
3. Verify configuration
4. Test images locally

### Resources

- [Docker Documentation](https://docs.docker.com/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Security](https://docs.docker.com/engine/security/)
