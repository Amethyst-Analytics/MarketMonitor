#!/usr/bin/env bash
set -euo pipefail

echo "Stopping MarketMonitor services..."

pkill -f "stream_service" || true
pkill -f "ui.backend" || true
pkill -f "streamlit run" || true

echo "Services stopped."
