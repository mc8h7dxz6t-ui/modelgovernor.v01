#!/usr/bin/env bash
# ModelGovernor pilot attestation — reserve → dispatch → verify-chain → anchor
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN="${SIDECAR_PRIMARY_TOKEN:-${SIDECAR_INTERNAL_TOKENS:-dev-sidecar-token}}"
TOKEN="${TOKEN%%,*}"
SIDECAR="${MG_SIDECAR_URL:-http://localhost:8081}"
GATEWAY="${MG_GATEWAY_URL:-http://localhost:8080}"

echo "==> ModelGovernor Pilot Attestation"
echo "    sidecar=$SIDECAR gateway=$GATEWAY"

curl -sf "$SIDECAR/readyz" >/dev/null
curl -sf "$GATEWAY/readyz" >/dev/null
echo "OK  spine ready"

OP_KEY="pilot-$(date +%s)"
curl -sf -X POST "$GATEWAY/governed/dispatch" \
  -H "x-internal-token: $TOKEN" \
  -H 'content-type: application/json' \
  -d "{\"user_id\":\"smoke-user\",\"trace_id\":\"trace-pilot\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"1.000000\",\"idempotency_key\":\"$OP_KEY\",\"prompt\":\"pilot attestation\"}" \
  >/dev/null
echo "OK  governed dispatch"

VERIFY="$(curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/ledger/verify-chain")"
echo "$VERIFY" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('valid') is True, d"
echo "OK  ledger chain verified"

ANCHOR="$(curl -sf -X POST -H "x-internal-token: $TOKEN" "$SIDECAR/internal/ledger/anchor-head")"
echo "$ANCHOR" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('anchored') or d.get('head_hash'), d"
echo "OK  chain head anchored"

cd "$ROOT"
python3 scripts/mg_attestation_runner.py

if [[ "${ATTESTATION_CI:-}" != "1" ]]; then
  make mg-certification-l4-ci
fi

echo "==> Pilot attestation complete"
