#!/usr/bin/env bash
# Live compose smoke for Finance Governor — spine 8090–8092 + verify-chain (requires Docker)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=compose-smoke-lib.sh
source "$ROOT/scripts/compose-smoke-lib.sh"
cd "$ROOT/finance-governor"

TOKEN="${FG_INTERNAL_TOKENS:-dev-fg-spine-token-change-me}"

echo "==> Starting FG stack (spine + hero platforms)..."
docker compose up -d --build \
  fg-postgres fg-redis fg-sidecar fg-reconciler fg-gateway fg-wirematch fg-algofreeze

echo "==> Gateway health (8090)"
wait_for_url http://localhost:8090/readyz

echo "==> Sidecar health (8091)"
wait_for_url http://localhost:8091/healthz

echo "==> governed commit"
curl -sf -X POST http://localhost:8090/governed/commit \
  -H "x-internal-token: $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"platform":"wire_match","operation_id":"smoke-fg-1","facets":{"amount":"100.00"},"policy_id":"wire-critical-us","reserved_exposure":"50","committed_exposure":"50"}' \
  >/dev/null

echo "==> verify-chain"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8091/internal/decisions/verify-chain \
  | python3 "$ROOT/scripts/chain_verify_assert.py"

echo "==> AlgoFreeze health + version mismatch freeze (8094)"
wait_for_url http://localhost:8094/healthz
curl -sf http://localhost:8094/healthz
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8094/orders \
  -H 'content-type: application/json' \
  -d '{"order_id":"smoke-af-1","runtime_sha":"wrong-deploy-sha"}')
test "$HTTP_CODE" = "403"

echo "==> WireMatch beneficiary mismatch HELD (8093)"
wait_for_url http://localhost:8093/healthz
curl -sf http://localhost:8093/healthz
curl -sf -X POST http://localhost:8093/wire/evaluate \
  -H 'content-type: application/json' \
  -d '{"wire_id":"smoke-wm-1","beneficiary_name":"Wrong Corp","beneficiary_account":"US99","reference":"x","amount":"7800000.00"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('decision')=='HELD', d"

echo "compose-smoke-fg OK"
