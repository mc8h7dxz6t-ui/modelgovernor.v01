#!/usr/bin/env bash
# Live compose smoke for Finance Governor — spine 8090–8092 + verify-chain (requires Docker)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/finance-governor"

TOKEN="${FG_INTERNAL_TOKENS:-dev-fg-spine-token-change-me}"

echo "==> Starting FG stack..."
docker compose up -d --build
sleep 8

echo "==> Gateway health (8090)"
curl -sf http://localhost:8090/readyz -H "x-internal-token: $TOKEN"

echo "==> Sidecar health (8091)"
curl -sf http://localhost:8091/healthz

echo "==> governed commit"
curl -sf -X POST http://localhost:8090/governed/commit \
  -H "x-internal-token: $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"platform":"wire_match","operation_id":"smoke-fg-1","facets":{"amount":"100.00"},"policy_id":"wire-critical-us","reserved_exposure":"50","committed_exposure":"50"}' \
  >/dev/null

echo "==> verify-chain"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8091/internal/decisions/verify-chain \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d"

echo "compose-smoke-fg OK"
