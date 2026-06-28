#!/usr/bin/env bash
# Finance Governor pilot attestation — crystallize → commit → verify-chain → anchor
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOKEN="${FG_INTERNAL_TOKENS:-dev-fg-spine-token-change-me}"
SIDECAR="${FG_SIDECAR_URL:-http://localhost:8091}"
GATEWAY="${FG_GATEWAY_URL:-http://localhost:8090}"

echo "==> Finance Governor Pilot Attestation"
echo "    sidecar=$SIDECAR gateway=$GATEWAY"

curl -sf "$SIDECAR/healthz" >/dev/null
curl -sf "$SIDECAR/readyz" >/dev/null
curl -sf "$GATEWAY/readyz" -H "x-internal-token: $TOKEN" >/dev/null
echo "OK  spine ready"

RESULT=$(curl -sf -X POST "$GATEWAY/governed/commit" \
  -H "x-internal-token: $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"platform":"wire_match","operation_id":"pilot-fg-1","facets":{"amount":"100.00","currency":"USD"},"policy_id":"wire-critical-us","reserved_exposure":"50","committed_exposure":"50"}')
echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('crystal_id'), d"
echo "OK  governed commit"

VERIFY="$(curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/decisions/verify-chain")"
echo "$VERIFY" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('valid') is True, d"
echo "OK  decision chain verified"

ANCHOR="$(curl -sf -X POST -H "x-internal-token: $TOKEN" "$SIDECAR/internal/decisions/anchor-head")"
echo "$ANCHOR" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('anchored') or d.get('head_hash'), d"
echo "OK  chain head anchored"

cd "$ROOT"
python3 finance-governor/scripts/fg_attestation_runner.py

if [[ "${ATTESTATION_CI:-}" != "1" ]]; then
  make fg-certification-l4-ci
fi

echo "==> Pilot attestation complete"
