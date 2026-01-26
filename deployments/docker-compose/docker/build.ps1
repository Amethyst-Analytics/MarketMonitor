$REGISTRY = if ($env:REGISTRY) { $env:REGISTRY } else { "marketmonitor" }
$TAG = if ($env:TAG) { $env:TAG } else { "latest" }

Write-Host "Building Docker images for $REGISTRY with tag $TAG"

docker build -f deployments/docker/streamer.Dockerfile -t "${REGISTRY}/streamer:${TAG}" .
docker build -f deployments/docker/ui-backend.Dockerfile -t "${REGISTRY}/ui-backend:${TAG}" .
docker build -f deployments/docker/ui-frontend.Dockerfile -t "${REGISTRY}/ui-frontend:${TAG}" .
docker build -f deployments/docker/catalog-service.Dockerfile -t "${REGISTRY}/catalog-service:${TAG}" .

Write-Host "Build complete. To push:"
Write-Host "docker push ${REGISTRY}/streamer:${TAG}"
Write-Host "docker push ${REGISTRY}/ui-backend:${TAG}"
Write-Host "docker push ${REGISTRY}/ui-frontend:${TAG}"
Write-Host "docker push ${REGISTRY}/catalog-service:${TAG}"
