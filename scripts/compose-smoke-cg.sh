#!/usr/bin/env bash
# Live compose smoke for CG — optional gate (requires Docker)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/cybersecurity-governor"

echo "==> Starting CG stack..."
docker compose up -d --build
sleep 8

echo "==> Gateway health (8120)"
curl -sf http://localhost:8120/readyz

echo "==> Sidecar health (8121)"
curl -sf http://localhost:8121/readyz

echo "==> EgressGovern health (8123)"
curl -sf http://localhost:8123/healthz

TOKEN="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"
echo "==> verify-chain"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8121/internal/security/verify-chain \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d"

echo "compose-smoke-cg OK"
