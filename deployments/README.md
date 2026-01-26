# Deployments

Deployment configurations and manifests for MarketMonitor across different environments.

## Overview

The `deployments` directory contains:

- **Docker Compose**: Local development setup
- **Kubernetes**: Production-ready manifests
- **Dockerfiles**: Container build configurations
- **Scripts**: Build and deployment utilities

## Directory Structure

```
deployments/
├─ docker-compose/          # Local Docker setup
│  ├─ docker-compose.yml    # Main compose file
│  └─ README.md            # Docker Compose guide
├─ k8s/                    # Kubernetes manifests
│  ├─ namespace.yaml        # Namespace definition
│  ├─ secrets.yaml          # Kubernetes secrets
│  ├─ timescaledb-statefulset.yaml  # TimescaleDB
│  ├─ redis-deployment.yaml  # Redis cache
│  ├─ streamer-deployment.yaml     # Stream service
│  ├─ ui-backend-deployment.yaml    # UI API
│  ├─ ui-frontend-deployment.yaml   # UI frontend
│  ├─ ingress.yaml          # Ingress configuration
│  ├─ catalog-cronjob.yaml  # Catalog sync jobs
│  ├─ kustomization.yaml    # Kustomize config
│  └─ README.md            # Kubernetes guide
├─ docker/                 # Docker build files
│  ├─ build.sh             # Linux/macOS build script
│  ├─ build.ps1            # Windows build script
│  └─ README.md            # Docker build guide
└─ README.md               # This file
```

## Quick Start

### Local Development with Docker Compose

```bash
cd deployments/docker-compose
docker compose up -d
```

This starts:

- TimescaleDB (port 5432)
- Redis (port 6379)

### Production Deployment with Kubernetes

```bash
cd deployments/k8s
kubectl apply -f .
# Or use kustomize:
kubectl apply -k .
```

## Environment Configuration

### Required Environment Variables

| Variable               | Description         | Local Default          | Production      |
| ---------------------- | ------------------- | ---------------------- | --------------- |
| `POSTGRES_PASSWORD`    | PostgreSQL password | `admin123`             | Set via secrets |
| `POSTGRES_DB`          | Database name       | `market_data`          | Set via secrets |
| `UPSTOX_CLIENT_ID`     | OAuth client ID     | Required               | Set via secrets |
| `UPSTOX_CLIENT_SECRET` | OAuth client secret | Required               | Set via secrets |
| `UPSTOX_ACCESS_TOKEN`  | OAuth access token  | Required               | Set via secrets |
| `UPSTOX_REDIS_URL`     | Redis URL           | `redis://redis:6379/0` | Set via secrets |
| `UPSTOX_PG_DSN`        | PostgreSQL DSN      | Auto-generated         | Set via secrets |

### Docker Compose Environment

Create `.env` in `deployments/docker-compose/`:

```bash
POSTGRES_PASSWORD=admin123
POSTGRES_DB=market_data
UPSTOX_CLIENT_ID=your_client_id
UPSTOX_CLIENT_SECRET=your_client_secret
UPSTOX_ACCESS_TOKEN=your_access_token
```

### Kubernetes Secrets

Create secrets before applying manifests:

```bash
kubectl create secret generic marketmonitor-secrets \
  --from-literal=POSTGRES_PASSWORD=admin123 \
  --from-literal=POSTGRES_DB=market_data \
  --from-literal=UPSTOX_CLIENT_ID=your_client_id \
  --from-literal=UPSTOX_CLIENT_SECRET=your_client_secret \
  --from-literal=UPSTOX_ACCESS_TOKEN=your_access_token \
  --from-literal=UPSTOX_PG_DSN=postgresql://postgres:admin123@timescaledb:5432/market_data \
  --from-literal=UPSTOX_REDIS_URL=redis://redis:6379/0
```

## Docker Compose

### Services

| Service       | Image                               | Ports | Description          |
| ------------- | ----------------------------------- | ----- | -------------------- |
| `timescaledb` | `timescale/timescaledb:latest-pg15` | 5432  | TimescaleDB database |
| `redis`       | `redis:7-alpine`                    | 6379  | Redis cache          |

### Persistence

Data is persisted in Docker volumes:

- `timescaledb_data`: PostgreSQL data
- `redis_data`: Redis data

### Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f timescaledb
docker compose logs -f redis

# Execute commands in containers
docker compose exec timescaledb psql -U postgres -d market_data
docker compose exec redis redis-cli
```

## Kubernetes

### Namespace

All resources are deployed in the `marketmonitor` namespace.

### Secrets

Sensitive data is stored in Kubernetes secrets:

- Database credentials
- OAuth tokens
- API keys

### ConfigMaps

Non-sensitive configuration is stored in ConfigMaps:

- Service settings
- Default values
- Configuration options

### Deployments

| Deployment    | Replicas | Resources           | Purpose        |
| ------------- | -------- | ------------------- | -------------- |
| `timescaledb` | 1        | 1Gi RAM, 500m CPU   | Database       |
| `redis`       | 1        | 256Mi RAM, 250m CPU | Cache          |
| `streamer`    | 1        | 1Gi RAM, 1000m CPU  | Data ingestion |
| `ui-backend`  | 1        | 512Mi RAM, 500m CPU | API server     |
| `ui-frontend` | 1        | 512Mi RAM, 500m CPU | Web UI         |

### Services

Each deployment has a corresponding Service for internal communication.

### Ingress

External access is configured via Ingress:

- `/api/*` → UI backend (port 8000)
- `/*` → UI frontend (port 8501)

### CronJobs

Automated tasks:

- `catalog-sync`: Daily Upstox catalog sync
- `mtf-sync`: Weekly MTF securities sync

### Commands

```bash
# Apply all manifests
kubectl apply -f .

# Apply with kustomize
kubectl apply -k .

# Check deployment status
kubectl get pods -n marketmonitor

# View logs
kubectl logs -f deployment/streamer -n marketmonitor

# Scale deployments
kubectl scale deployment streamer --replicas=2 -n marketmonitor

# Delete resources
kubectl delete -f .
```

## Docker

### Build Images

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

### Images Built

| Image                           | Tag    | Description          |
| ------------------------------- | ------ | -------------------- |
| `marketmonitor/streamer`        | latest | Stream service       |
| `marketmonitor/ui-backend`      | latest | FastAPI backend      |
| `marketmonitor/ui-frontend`     | latest | Streamlit frontend   |
| `marketmonitor/catalog-service` | latest | Catalog sync service |

### Dockerfiles

Each service has its own Dockerfile:

- `streamer.Dockerfile`
- `ui-backend.Dockerfile`
- `ui-frontend.Dockerfile`
- `catalog-service.Dockerfile`

### Multi-stage Builds

All Dockerfiles use multi-stage builds:

- **Build stage**: Install dependencies
- **Runtime stage**: Copy only necessary files
- **Optimized**: Minimal runtime image

## Environment-Specific Configurations

### Development

- **Docker Compose**: Quick local setup
- **Minikube**: Local Kubernetes testing
- **Debug logging**: Verbose output enabled

### Staging

- **Kubernetes**: Production-like setup
- **Resource limits**: Constrained resources
- **Monitoring**: Health checks enabled

### Production

- **Kubernetes**: Full production setup
- **High availability**: Multiple replicas
- **Monitoring**: Full observability stack
- **Security**: Network policies, RBAC

## Monitoring

### Health Checks

All services include health checks:

- **Liveness**: Service is running
- **Readiness**: Service is ready for traffic
- **Startup**: Service is starting up

### Metrics

Consider adding Prometheus metrics:

- Application metrics
- Infrastructure metrics
- Business metrics

### Logging

Structured logging with:

- JSON format for log aggregation
- Correlation IDs for tracing
- Error tracking

## Security

### Network Policies

Implement Kubernetes network policies:

- Restrict inter-service communication
- Allow only necessary ports
- Default deny all traffic

### RBAC

Role-based access control:

- Service accounts for each service
- Minimal permissions
- Audit access logs

### Secrets Management

- Use Kubernetes secrets
- Rotate secrets regularly
- Audit secret access

## Backup and Recovery

### Database Backup

```bash
# TimescaleDB backup
kubectl exec -n marketmonitor deployment/timescaledb -- pg_dump -U postgres market_data > backup.sql

# Restore
kubectl exec -i -n marketmonitor deployment/timescaledb -- psql -U postgres market_data < backup.sql
```

### Persistent Volumes

- Use PersistentVolumeClaims
- Configure appropriate storage classes
- Implement backup strategies

## Troubleshooting

### Common Issues

1. **Pods Not Starting**
   - Check resource requests/limits
   - Verify image availability
   - Check secret/configmap references

2. **Database Connection Failed**
   - Verify secret values
   - Check network policies
   - Validate service endpoints

3. **High Resource Usage**
   - Monitor resource metrics
   - Check for memory leaks
   - Optimize application code

### Debug Commands

```bash
# Check pod status
kubectl describe pod <pod-name> -n marketmonitor

# Check events
kubectl get events -n marketmonitor --sort-by='.lastTimestamp'

# Port-forward to local
kubectl port-forward deployment/ui-backend 8000:8000 -n marketmonitor

# Exec into pod
kubectl exec -it <pod-name> -n marketmonitor -- /bin/bash
```

## Performance Tuning

### Database Optimization

- Connection pooling
- Query optimization
- Index tuning
- Partitioning strategies

### Resource Optimization

- Right-size containers
- Use resource limits
- Implement HPA (Horizontal Pod Autoscaler)
- Consider VPA (Vertical Pod Autoscaler)

### Caching Strategies

- Redis for hot data
- Application-level caching
- CDN for static assets

## CI/CD Integration

### GitHub Actions

Automated deployment pipeline:

1. Build Docker images
2. Push to registry
3. Update Kubernetes manifests
4. Deploy to staging/production

### ArgoCD

GitOps deployment:

- Git repository as source of truth
- Automatic synchronization
- Rollback capabilities

## Maintenance

### Regular Tasks

- Update container images
- Rotate secrets
- Update dependencies
- Monitor resource usage
- Backup data

### Updates

- Rolling updates for zero downtime
- Blue-green deployments
- Canary deployments
- A/B testing

## Best Practices

### Security

- Use least privilege principle
- Regular security scans
- Keep dependencies updated
- Monitor for vulnerabilities

### Reliability

- Implement health checks
- Use proper logging
- Monitor key metrics
- Plan for failures

### Scalability

- Design for horizontal scaling
- Use load balancing
- Implement caching
- Optimize database queries

### Observability

- Structured logging
- Metrics collection
- Distributed tracing
- Error tracking

## Documentation

- Keep documentation updated
- Document deployment procedures
- Maintain runbooks
- Provide troubleshooting guides

## Support

### Getting Help

- Check documentation first
- Review logs for errors
- Use debugging commands
- Contact support team

### Contributing

- Follow deployment standards
- Update documentation
- Test changes thoroughly
- Submit pull requests
