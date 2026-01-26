# Kubernetes

Production-ready Kubernetes manifests for MarketMonitor deployment.

## Overview

This directory contains Kubernetes manifests for deploying MarketMonitor in a production environment with:

- **High Availability**: Multiple replicas and resource management
- **Security**: Secrets management and network policies
- **Scalability**: Horizontal pod autoscaling
- **Observability**: Health checks and monitoring

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Sufficient resources (minimum 4GB RAM, 2 CPU cores)
- Ingress controller (nginx, traefik, etc.)

## Quick Start

### Deploy All Resources

```bash
cd deployments/k8s
kubectl apply -f .
```

### Deploy with Kustomize

```bash
cd deployments/k8s
kubectl apply -k .
```

### Verify Deployment

```bash
kubectl get pods -n marketmonitor
kubectl get services -n marketmonitor
kubectl get ingress -n marketmonitor
```

## Architecture

### Namespace

All resources are deployed in the `marketmonitor` namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: marketmonitor
```

### Secrets

Sensitive configuration stored in Kubernetes secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: marketmonitor-secrets
  namespace: marketmonitor
type: Opaque
stringData:
  POSTGRES_PASSWORD: "admin123"
  POSTGRES_DB: "market_data"
  UPSTOX_CLIENT_ID: "your_client_id"
  UPSTOX_CLIENT_SECRET: "your_client_secret"
  UPSTOX_ACCESS_TOKEN: "your_access_token"
  UPSTOX_PG_DSN: "postgresql://postgres:admin123@timescaledb:5432/market_data"
  UPSTOX_REDIS_URL: "redis://redis:6379/0"
```

### ConfigMaps

Non-sensitive configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: marketmonitor-config
  namespace: marketmonitor
data:
  UPSTOX_REDIRECT_HOST: "localhost"
  UPSTOX_REDIRECT_PORT: "8080"
  UPSTOX_REDIRECT_PATH: "/upstox_auth"
  UPSTOX_INSTRUMENT_FILE: "complete_data_formatted.json"
  UPSTOX_STREAM_MODE: "ltpc"
  UPSTOX_PG_BATCH: "1000"
  UPSTOX_PG_FLUSH_INTERVAL: "0.5"
  UPSTOX_REDIS_TTL: "10"
```

## Services

### TimescaleDB

StatefulSet for PostgreSQL with TimescaleDB extension:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: timescaledb
  namespace: marketmonitor
spec:
  serviceName: timescaledb
  replicas: 1
  selector:
    matchLabels:
      app: timescaledb
  template:
    metadata:
      labels:
        app: timescaledb
    spec:
      containers:
        - name: timescaledb
          image: timescale/timescaledb:latest-pg15
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: marketmonitor-secrets
                  key: POSTGRES_PASSWORD
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: marketmonitor-secrets
                  key: POSTGRES_DB
          volumeMounts:
            - name: timescaledb-data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
          livenessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - postgres
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - postgres
            initialDelaySeconds: 5
            periodSeconds: 5
  volumeClaimTemplates:
    - metadata:
        name: timescaledb-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

### Redis

Deployment for Redis cache:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: marketmonitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            exec:
              command:
                - redis-cli
                - ping
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - redis-cli
                - ping
            initialDelaySeconds: 3
            periodSeconds: 5
```

### Stream Service

Deployment for market data ingestion:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: streamer
  namespace: marketmonitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: streamer
  template:
    metadata:
      labels:
        app: streamer
    spec:
      containers:
        - name: streamer
          image: marketmonitor/streamer:latest
          envFrom:
            - secretRef:
                name: marketmonitor-secrets
            - configMapRef:
                name: marketmonitor-config
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          livenessProbe:
            exec:
              command:
                - python
                - -c
                - "import sys; sys.exit(0)"
            initialDelaySeconds: 30
            periodSeconds: 60
          readinessProbe:
            exec:
              command:
                - python
                - -c
                - "import sys; sys.exit(0)"
            initialDelaySeconds: 10
            periodSeconds: 30
```

### UI Backend

FastAPI backend service:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ui-backend
  namespace: marketmonitor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ui-backend
  template:
    metadata:
      labels:
        app: ui-backend
    spec:
      containers:
        - name: ui-backend
          image: marketmonitor/ui-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: marketmonitor-secrets
            - configMapRef:
                name: marketmonitor-config
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 3
            periodSeconds: 5
```

### UI Frontend

Streamlit frontend service:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ui-frontend
  namespace: marketmonitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ui-frontend
  template:
    metadata:
      labels:
        app: ui-frontend
    spec:
      containers:
        - name: ui-frontend
          image: marketmonitor/ui-frontend:latest
          ports:
            - containerPort: 8501
          env:
            - name: BACKEND_URL
              value: "http://ui-backend:8000"
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /_stcore/health
              port: 8501
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /_stcore/health
              port: 8501
            initialDelaySeconds: 5
            periodSeconds: 10
```

## Networking

### Services

Each deployment has a corresponding Service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: timescaledb
  namespace: marketmonitor
spec:
  selector:
    app: timescaledb
  ports:
    - port: 5432
      targetPort: 5432
  type: ClusterIP
```

### Ingress

External access configuration:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: marketmonitor
  namespace: marketmonitor
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  ingressClassName: nginx
  rules:
    - host: marketmonitor.local
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: ui-backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ui-frontend
                port:
                  number: 8501
```

## Automation

### CronJobs

#### Catalog Sync

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: catalog-sync
  namespace: marketmonitor
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
                - configMapRef:
                    name: marketmonitor-config
              resources:
                requests:
                  memory: "256Mi"
                  cpu: "250m"
                limits:
                  memory: "512Mi"
                  cpu: "500m"
          restartPolicy: OnFailure
```

#### MTF Sync

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mtf-sync
  namespace: marketmonitor
spec:
  schedule: "0 3 * * 0"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: mtf-sync
              image: marketmonitor/catalog-service:latest
              command: ["python", "-m", "catalog_service.mtf_loader"]
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

## Configuration Management

### Kustomize

Use Kustomize for environment-specific configurations:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
metadata:
  name: marketmonitor
resources:
  - namespace.yaml
  - secrets.yaml
  - timescaledb-statefulset.yaml
  - redis-deployment.yaml
  - streamer-deployment.yaml
  - ui-backend-deployment.yaml
  - ui-frontend-deployment.yaml
  - ingress.yaml
  - catalog-cronjob.yaml
commonLabels:
  app.kubernetes.io/name: marketmonitor
  app.kubernetes.io/component: backend
namespace: marketmonitor
```

### Environment Overrides

Create overlays for different environments:

```
k8s/
├─ base/
│  ├─ kustomization.yaml
│  └─ manifests/
├─ overlays/
│  ├─ development/
│  │  ├─ kustomization.yaml
│  │  └─ patches/
│  └─ production/
│      ├─ kustomization.yaml
│      └─ patches/
```

## Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ui-backend-hpa
  namespace: marketmonitor
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ui-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Vertical Pod Autoscaler

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: streamer-vpa
  namespace: marketmonitor
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: streamer
  updatePolicy:
    updateMode: "Recreate"
  resourcePolicy:
    minAllowed:
      cpu: 100m
      memory: 256Mi
    maxAllowed:
      cpu: 2000m
      memory: 4Gi
```

## Monitoring

### Metrics Server

Deploy Prometheus metrics server:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: metrics-server
  namespace: marketmonitor
spec:
  selector:
    app.kubernetes.io/name: metrics-server
  ports:
    - port: 443
      targetPort: 443
```

### Pod Monitoring

```yaml
apiVersion: v1
kind: PodMonitor
metadata:
  name: marketmonitor-pods
  namespace: marketmonitor
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: marketmonitor
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

## Security

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: marketmonitor-netpol
  namespace: marketmonitor
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: marketmonitor
```

### RBAC

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: marketmonitor
  name: marketmonitor-role
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]
```

## Backup and Recovery

### Database Backup

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: marketmonitor
spec:
  schedule: "0 1 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: postgres-backup
              image: postgres:15
              command:
                - /bin/bash
                - -c
                - |
                  pg_dump -h timescaledb -U postgres market_data | gzip > /backup/backup-$(date +%Y%m%d).sql.gz
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: marketmonitor-secrets
                      key: POSTGRES_PASSWORD
              volumeMounts:
                - name: backup-storage
                  mountPath: /backup
          volumes:
            - name: backup-storage
              persistentVolumeClaim:
                claimName: backup-pvc
```

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n marketmonitor

# Check events
kubectl get events -n marketmonitor --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n marketmonitor
```

#### Database Connection Issues

```bash
# Check database pod
kubectl logs -f deployment/timescaledb -n marketmonitor

# Test database connection
kubectl exec -it deployment/timescaledb -n marketmonitor -- psql -U postgres -d market_data -c "SELECT 1;"
```

#### Service Discovery

```bash
# Check services
kubectl get svc -n marketmonitor

# Test service connectivity
kubectl exec -it deployment/ui-backend -n marketmonitor -- curl http://ui-backend:8000/health
```

### Debug Commands

```bash
# Port-forward to local
kubectl port-forward deployment/ui-backend 8000:8000 -n marketmonitor

# Exec into pod
kubectl exec -it <pod-name> -n marketmonitor -- /bin/bash

# Check logs
kubectl logs -f deployment/streamer -n marketmonitor
```

## Maintenance

### Rolling Updates

```bash
# Update deployment
kubectl set image deployment/streamer streamer=marketmonitor/streamer:v2 -n marketmonitor

# Check rollout status
kubectl rollout status deployment/streamer -n marketmonitor

# Rollback if needed
kubectl rollout undo deployment/streamer -n marketmonitor
```

### Resource Management

```bash
# Scale deployment
kubectl scale deployment/ui-backend --replicas=3 -n marketmonitor

# Check resource usage
kubectl describe node
kubectl top nodes
kubectl top pods -n marketmonitor
```

## Best Practices

### Resource Management

- Set appropriate resource requests and limits
- Use Horizontal Pod Autoscaling
- Monitor resource utilization
- Implement Vertical Pod Autoscaling

### Security

- Use NetworkPolicies to restrict traffic
- Implement RBAC for access control
- Use Secrets for sensitive data
- Regularly update images

### Reliability

- Implement health checks
- Use multiple replicas for critical services
- Set up proper monitoring and alerting
- Plan for disaster recovery

### Observability

- Use structured logging
- Implement metrics collection
- Set up distributed tracing
- Monitor application performance

## Support

### Getting Help

1. Check Kubernetes documentation
2. Review pod logs and events
3. Verify configuration
4. Check resource constraints

### Training Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [TimescaleDB on Kubernetes](https://docs.timescale.com/latest/timescaledb/latest/how-to-guides/kubernetes/)
- [Redis on Kubernetes](https://redis.io/docs/latest/operate/oss_and_stack/management/kubernetes/)
