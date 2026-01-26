#!/usr/bin/env bash
set -euo pipefail

REGISTRY=${REGISTRY:-marketmonitor}
TAG=${TAG:-latest}

echo "Building Docker images for $REGISTRY with tag $TAG"

docker build -f deployments/docker/streamer.Dockerfile -t $REGISTRY/streamer:$TAG .
docker build -f deployments/docker/ui-backend.Dockerfile -t $REGISTRY/ui-backend:$TAG .
docker build -f deployments/docker/ui-frontend.Dockerfile -t $REGISTRY/ui-frontend:$TAG .
docker build -f deployments/docker/catalog-service.Dockerfile -t $REGISTRY/catalog-service:$TAG .

echo "Build complete. To push:"
echo "docker push $REGISTRY/streamer:$TAG"
echo "docker push $REGISTRY/ui-backend:$TAG"
echo "docker push $REGISTRY/ui-frontend:$TAG"
echo "docker push $REGISTRY/catalog-service:$TAG"
