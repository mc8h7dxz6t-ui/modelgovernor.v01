#!/usr/bin/env bash
# fg-demo-up — boot Finance Governor stack (standalone)
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --build
echo "waiting for sidecar..."
for i in $(seq 1 30); do
  curl -sf http://localhost:8091/healthz >/dev/null && break
  sleep 2
done
curl -sf http://localhost:8091/healthz
echo "fg-demo-up OK"
