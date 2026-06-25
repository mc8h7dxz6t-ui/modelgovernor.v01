#!/usr/bin/env bash
# Insurance Governor pilot attestation — end-to-end spine + platform demo
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOKEN="${IG_INTERNAL_TOKENS:-dev-ig-spine-token-change-me}"
SIDECAR="${IG_SIDECAR_URL:-http://localhost:8101}"
GATEWAY="${IG_GATEWAY_URL:-http://localhost:8100}"

echo "==> Insurance Governor Pilot Attestation"
echo "    sidecar=$SIDECAR gateway=$GATEWAY"

curl -sf "$SIDECAR/readyz" >/dev/null
curl -sf "$GATEWAY/readyz" >/dev/null
echo "OK  spine ready"

curl -sf -X POST "$GATEWAY/governed/commit" \
  -H 'content-type: application/json' \
  -d '{"platform":"claim_gate","operation_id":"pilot-claim-1","facets":{"claim_id":"pilot-claim-1","payout_amount":"100.00"},"policy_id":"claim-high-us","reserved_reserve":"100","committed_reserve":"100","outcome":"paid"}' \
  >/dev/null
echo "OK  governed commit"

VERIFY="$(curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/claims/verify-chain")"
echo "$VERIFY" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('valid') is True, d"
echo "OK  claim chain verified"

ANCHOR="$(curl -sf -X POST -H "x-internal-token: $TOKEN" "$SIDECAR/internal/claims/anchor-head")"
echo "$ANCHOR" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('anchored') or d.get('head_hash'), d"
echo "OK  chain head anchored"

if curl -sf http://localhost:8103/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8103/claim/evaluate \
    -H 'content-type: application/json' \
    -d '{"claim_id":"pilot-gate-1","payout_amount":"5000.00"}' >/dev/null
  echo "OK  ClaimGate evaluate"
fi

if curl -sf http://localhost:8104/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8104/bind/evaluate \
    -H 'content-type: application/json' \
    -d '{"application_id":"pilot-bind-1","premium":"10000.00","limit":"500000.00"}' >/dev/null
  echo "OK  BindAuthority evaluate"
fi

if curl -sf http://localhost:8105/healthz >/dev/null 2>&1; then
  HASH="$(python3 - <<'PY'
import hashlib
payload = '{"magnitude":7.2}'
print(hashlib.sha256(f"usgs-feed:{payload}".encode()).hexdigest())
PY
)"
  curl -sf -X POST http://localhost:8105/trigger/evaluate \
    -H 'content-type: application/json' \
    -d "{\"event_id\":\"pilot-trig-1\",\"metric_value\":\"7.2\",\"threshold\":\"6.5\",\"oracle_source\":\"usgs-feed\",\"oracle_payload\":\"{\\\"magnitude\\\":7.2}\",\"oracle_attestation_hash\":\"$HASH\",\"payout_reserve\":\"50000.00\"}" >/dev/null
  echo "OK  ParametricOracle evaluate"
fi

cd "$ROOT"
make ig-certification
echo "==> Pilot attestation complete"
