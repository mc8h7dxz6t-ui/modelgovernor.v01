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

echo "==> AlgoFreeze health + version mismatch freeze (8094)"
curl -sf http://localhost:8094/healthz
curl -sf -o /dev/null -w "%{http_code}" -X POST http://localhost:8094/orders \
  -H 'content-type: application/json' \
  -d '{"order_id":"smoke-af-1","runtime_sha":"wrong-deploy-sha"}' | grep -q 403

echo "==> WireMatch beneficiary mismatch HELD (8093)"
curl -sf http://localhost:8093/healthz
curl -sf -X POST http://localhost:8093/wire/evaluate \
  -H 'content-type: application/json' \
  -d '{"wire_id":"smoke-wm-1","beneficiary_name":"Wrong Corp","beneficiary_account":"US99","reference":"x","amount":"7800000.00"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('decision')=='HELD', d"

echo "compose-smoke-fg OK"
