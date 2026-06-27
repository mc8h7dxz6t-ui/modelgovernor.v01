#!/usr/bin/env bash
# fg-demo-gold-reliability — drift lockout, regulatory export, attribution, guardrails
set -euo pipefail

TOKEN="${FG_INTERNAL_TOKEN:-dev-fg-spine-token-change-me}"
SIDECAR="${FG_SIDECAR_URL:-http://localhost:8091}"

step() { echo ""; echo "=== Reliability $1: $2 ==="; }

step 1 "Drift lockout demo"
FACETS='{"amount":"100.00","desk_id":"desk-default"}'
CRYSTAL=$(curl -sf -X POST "$SIDECAR/crystallize" -H "x-internal-token: $TOKEN" -H 'content-type: application/json' \
  -d "{\"platform\":\"wire_match\",\"operation_id\":\"fg-drift-demo-$(date +%s)\",\"account_id\":\"desk-default\",\"risk_tier\":\"high\",\"facets\":$FACETS,\"policy_id\":\"wire-critical-us\",\"reserved_exposure\":\"100.00\"}")
CID=$(echo "$CRYSTAL" | python3 -c "import sys,json; print(json.load(sys.stdin)['crystal_id'])")
COMMIT=$(curl -sf -X POST "$SIDECAR/commit" -H "x-internal-token: $TOKEN" -H 'content-type: application/json' \
  -d "{\"crystal_id\":\"$CID\",\"facets\":$FACETS,\"committed_exposure\":\"200.00\",\"outcome\":\"over_commit\"}")
echo "$COMMIT"

step 2 "Account locked after drift"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/guardrail/incidents?limit=3" | python3 -m json.tool

step 3 "Regulatory export bundle"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/regulatory/export?limit=10" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'chain_verification' in d and 'guardrail_incidents' in d; print('export keys:', sorted(d.keys()))"

step 4 "Attribution summary"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/attribution/summary" | python3 -m json.tool

step 5 "Chain verify still valid"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/decisions/verify-chain" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d; print('chain valid, events=', d.get('event_count'))"

echo ""
echo "fg-demo-gold-reliability complete."
