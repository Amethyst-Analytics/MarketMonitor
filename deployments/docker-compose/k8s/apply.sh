#!/usr/bin/env bash
set -euo pipefail

kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f timescaledb-statefulset.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f streamer-deployment.yaml
kubectl apply -f ui-backend-deployment.yaml
kubectl apply -f ui-frontend-deployment.yaml
kubectl apply -f ingress.yaml
kubectl apply -f catalog-cronjob.yaml

echo "Deployed to namespace marketmonitor"
echo "UI will be available at http://marketmonitor.local (ensure DNS/hosts entry)"
