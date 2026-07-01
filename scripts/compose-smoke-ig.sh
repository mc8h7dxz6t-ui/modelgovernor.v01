#!/usr/bin/env bash
# Live compose smoke for Insurance Governor — spine 8100–8102, ClaimGate 8103, sandbox FNOL+rail
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IG="$ROOT/insurance-governor"
# shellcheck source=compose-smoke-lib.sh
source "$ROOT/scripts/compose-smoke-lib.sh"
TOKEN="${IG_INTERNAL_TOKENS:-dev-ig-spine-token-change-me}"

cleanup() {
  kill "${FEDNOW_PID:-}" "${PAS_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Starting PAS + FedNow sandbox mocks..."
python3 "$IG/scripts/mock_fednow_sandbox.py" &
FEDNOW_PID=$!
python3 "$IG/scripts/mock_pas_writeback_sandbox.py" &
PAS_PID=$!
sleep 2
curl -sf http://localhost:8190/v1/payments -X POST -H 'content-type: application/json' -d '{"idempotencyKey":"probe"}' >/dev/null || {
  echo "FedNow sandbox mock failed to start" >&2
  exit 1
}

cd "$IG"
echo "==> Starting IG stack (spine + ClaimGate + demo wedges)..."
docker compose -f docker-compose.yml -f docker-compose.wave3.yml up -d --build \
  ig-postgres ig-redis ig-sidecar ig-reconciler ig-gateway ig-claim-gate \
  ig-spatial-twin ig-subrogation-graph

echo "==> Gateway health (8100)"
wait_for_url http://localhost:8100/readyz
curl -sf http://localhost:8100/readyz

echo "==> Sidecar health (8101)"
wait_for_url http://localhost:8101/readyz
curl -sf http://localhost:8101/readyz

echo "==> ClaimGate health (8103)"
wait_for_url http://localhost:8103/healthz 60
curl -sf http://localhost:8103/healthz

echo "==> governed commit"
curl -sf -X POST http://localhost:8100/governed/commit \
  -H 'content-type: application/json' \
  -d '{"platform":"claim_gate","operation_id":"smoke-ig-1","facets":{"claim_id":"smoke-ig-1","payout_amount":"100.00"},"policy_id":"claim-high-us","reserved_reserve":"50","committed_reserve":"50","outcome":"paid"}' \
  >/dev/null

echo "==> verify-chain"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8101/internal/claims/verify-chain \
  | python3 "$ROOT/scripts/chain_verify_assert.py"

echo "==> FNOL Guidewire webhook (live PAS writeback)"
FNOL_GW=$(curl -sf -X POST http://localhost:8103/claim/fnol/webhook \
  -H 'content-type: application/json' \
  -d '{"vendor":"guidewire","payload":{"claim":{"claimNumber":"smoke-fnol-gw","reportedAmount":"100.00","policyNumber":"POL-AUTO-001","lossDate":"2025-06-01","id":"gw-smoke-1"}}}')
echo "$FNOL_GW" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('writeback_status')=='synced', d; assert d.get('writeback_external_ref'), d"

echo "==> FNOL Snapsheet webhook (live PAS writeback)"
FNOL_SS=$(curl -sf -X POST http://localhost:8103/claim/fnol/webhook \
  -H 'content-type: application/json' \
  -d '{"vendor":"snapsheet","payload":{"data":{"claim_number":"smoke-fnol-ss","reserve_amount":"100.00","policy_number":"POL-AUTO-001","date_of_loss":"2025-06-01","id":"ss-smoke-1"}}}')
echo "$FNOL_SS" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('writeback_status')=='synced', d"

PAS_STATS=$(curl -sf http://localhost:8191/stats)
echo "$PAS_STATS" | python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d.get('writebacks',[]))>=2, d"

echo "==> FedNow sandbox rail (governed payout)"
RAIL=$(curl -sf -X POST http://localhost:8103/claim/evaluate \
  -H 'content-type: application/json' \
  -d '{"claim_id":"smoke-rail-1","payout_amount":"100.00","policy_number":"POL-AUTO-001","idempotency_key":"smoke-rail-1","payee_id":"sandbox-payee"}')
echo "$RAIL" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('payment_status')=='COMPLETED', d; assert str(d.get('payment_id','')).startswith('pay_') or d.get('payment_id'), d"

echo "==> SpatialTwin demo wedge"
chmod +x "$ROOT/insurance-governor/scripts/spatial-twin-demo.sh"
SPATIAL_TWIN_URL=http://localhost:8107 "$ROOT/insurance-governor/scripts/spatial-twin-demo.sh"

echo "==> SubrogationGraph demo wedge"
chmod +x "$ROOT/insurance-governor/scripts/subrogation-graph-demo.sh"
SUBROGATION_GRAPH_URL=http://localhost:8109 "$ROOT/insurance-governor/scripts/subrogation-graph-demo.sh"

echo "compose-smoke-ig OK"
