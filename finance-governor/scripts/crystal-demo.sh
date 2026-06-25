#!/usr/bin/env bash
# crystal-demo — 3-minute Crystal Commit Protocol walkthrough
set -euo pipefail

TOKEN="${FG_INTERNAL_TOKEN:-dev-fg-spine-token-change-me}"
SIDECAR="${FG_SIDECAR_URL:-http://localhost:8091}"
GATEWAY="${FG_GATEWAY_URL:-http://localhost:8090}"
WIREMATCH="${WIREMATCH_URL:-http://localhost:8093}"
ALGOFREEZE="${ALGOFREEZE_URL:-http://localhost:8094}"

step() { echo ""; echo "=== Step $1: $2 ==="; }

step 1 "Spine health"
curl -sf "$SIDECAR/healthz" | tee /tmp/crystal-demo-health.json
echo ""

step 2 "Crystallize + commit (governed wire)"
RESULT=$(curl -sf -X POST "$GATEWAY/governed/commit" \
  -H 'content-type: application/json' \
  -d '{
    "platform": "wire_match",
    "operation_id": "crystal-demo-wire-1",
    "facets": {"amount": "7800000.00", "currency": "USD", "beneficiary_hash": "US12REV001"},
    "policy_id": "wire-critical-us",
    "reserved_exposure": "100.00",
    "committed_exposure": "100.00",
    "outcome": "approved"
  }')
echo "$RESULT"
CRYSTAL_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['crystal_id'])")

step 3 "Forensic reconstruct (examiner view)"
curl -sf -H "x-internal-token: $TOKEN" \
  "$SIDECAR/internal/crystals/$CRYSTAL_ID/reconstruct" | python3 -m json.tool | head -40

step 4 "WireMatch HELD on $900M-class amount anomaly"
curl -sf -X POST "$WIREMATCH/wire/evaluate" \
  -H 'content-type: application/json' \
  -d '{
    "wire_id": "crystal-demo-anomaly",
    "beneficiary_name": "Revlon Lenders Group",
    "beneficiary_account": "US12REV001",
    "reference": "payment",
    "amount": "900000000.00"
  }' | python3 -m json.tool

step 5 "AlgoFreeze — version mismatch freezes desk (Knight-class)"
curl -sf -X POST "$ALGOFREEZE/orders" \
  -H 'content-type: application/json' \
  -d '{"order_id": "crystal-demo-algo", "runtime_sha": "wrong-deploy-sha"}' \
  || echo "(expected 403 freeze)"

curl -sf "$ALGOFREEZE/status" | python3 -m json.tool

step 6 "Recent spine events"
curl -sf -H "x-internal-token: $TOKEN" \
  "$SIDECAR/internal/events/recent?limit=5" | python3 -m json.tool

echo ""
echo "crystal-demo complete — No commit without a Crystal."
