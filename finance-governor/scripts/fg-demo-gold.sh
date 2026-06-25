#!/usr/bin/env bash
# fg-demo-gold — institutional++ walkthrough (Finance Governor standalone)
set -euo pipefail

TOKEN="${FG_INTERNAL_TOKEN:-dev-fg-spine-token-change-me}"
SIDECAR="${FG_SIDECAR_URL:-http://localhost:8091}"
GATEWAY="${FG_GATEWAY_URL:-http://localhost:8090}"
WIREMATCH="${WIREMATCH_URL:-http://localhost:8093}"
ALGOFREEZE="${ALGOFREEZE_URL:-http://localhost:8094}"

step() { echo ""; echo "=== Step $1: $2 ==="; }

step 1 "Stack health"
curl -sf "$SIDECAR/healthz" && curl -sf "$SIDECAR/readyz" && curl -sf "$GATEWAY/readyz" -H "x-internal-token: $TOKEN"

step 2 "Governed commit (CCP wire)"
RESULT=$(curl -sf -X POST "$GATEWAY/governed/commit" \
  -H "x-internal-token: $TOKEN" \
  -H 'content-type: application/json' \
  -d '{
    "platform": "wire_match",
    "operation_id": "fg-gold-wire-1",
    "facets": {"amount": "7800000.00", "currency": "USD"},
    "policy_id": "wire-critical-us",
    "reserved_exposure": "100.00",
    "committed_exposure": "100.00"
  }')
echo "$RESULT"
CRYSTAL_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['crystal_id'])")

step 3 "Forensic reconstruct"
curl -sf -H "x-internal-token: $TOKEN" \
  "$SIDECAR/internal/crystals/$CRYSTAL_ID/reconstruct" | python3 -m json.tool | head -30

step 4 "Decision chain verify"
curl -sf -H "x-internal-token: $TOKEN" \
  "$SIDECAR/internal/decisions/verify-chain" | python3 -m json.tool

step 5 "Anchor chain head (DB + optional S3)"
curl -sf -X POST -H "x-internal-token: $TOKEN" \
  "$SIDECAR/internal/decisions/anchor-head" | python3 -m json.tool

step 6 "WireMatch amount anomaly HELD"
curl -sf -X POST "$WIREMATCH/wire/evaluate" \
  -H 'content-type: application/json' \
  -d '{"wire_id":"fg-gold-anomaly","beneficiary_name":"Revlon Lenders Group","beneficiary_account":"US12REV001","reference":"payment","amount":"900000000.00"}' \
  | python3 -m json.tool

step 7 "AlgoFreeze version mismatch freeze"
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$ALGOFREEZE/orders" \
  -H 'content-type: application/json' \
  -d '{"order_id":"fg-gold-algo","runtime_sha":"wrong-sha"}' | grep -q 403
curl -sf "$ALGOFREEZE/status" | python3 -m json.tool

step 8 "Crystal mesh — wire blocked while algo frozen"
FREEZE=$(curl -sf -X POST "$SIDECAR/crystallize" -H "x-internal-token: $TOKEN" -H 'content-type: application/json' \
  -d '{"platform":"algofreeze","operation_id":"fg-gold-mesh-freeze","risk_tier":"critical","facets":{"freeze_state":"FROZEN"}}')
echo "$FREEZE"
WIRE=$(curl -sf -X POST "$SIDECAR/crystallize" -H "x-internal-token: $TOKEN" -H 'content-type: application/json' \
  -d '{"platform":"wire_match","operation_id":"fg-gold-mesh-wire","risk_tier":"high","facets":{"amount":"100.00"}}')
WID=$(echo "$WIRE" | python3 -c "import sys,json; print(json.load(sys.stdin)['crystal_id'])")
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$SIDECAR/commit" -H "x-internal-token: $TOKEN" -H 'content-type: application/json' \
  -d "{\"crystal_id\":\"$WID\",\"facets\":{\"amount\":\"100.00\"},\"committed_exposure\":\"0\"}" | grep -q 409

step 9 "Diagnostic status"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/diagnostic/status" | python3 -m json.tool

step 10 "Recent events + admin audit"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/events/recent?limit=5" | python3 -m json.tool
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/admin/audit/recent?limit=5" | python3 -m json.tool

step 11 "Invariant metrics"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/metrics" | python3 -m json.tool

echo ""
echo "fg-demo-gold complete — Finance Governor institutional++ (standalone)."
