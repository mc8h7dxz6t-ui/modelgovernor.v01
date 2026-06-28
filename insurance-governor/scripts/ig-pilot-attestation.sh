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
    -d '{"claim_id":"pilot-gate-1","payout_amount":"5000.00","policy_number":"POL-AUTO-001","idempotency_key":"pilot-pay-1"}' >/dev/null
  echo "OK  ClaimGate evaluate"
  curl -sf -X POST http://localhost:8103/claim/fnol/webhook \
    -H 'content-type: application/json' \
    -d '{"vendor":"guidewire","payload":{"claim":{"claimNumber":"pilot-fnol-1","reportedAmount":"8000.00","policyNumber":"POL-AUTO-001","lossDate":"2025-06-01","id":"gw-evt-1"}}}' >/dev/null
  echo "OK  ClaimGate FNOL webhook (Guidewire)"
fi

if curl -sf http://localhost:8104/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8104/bind/evaluate \
    -H 'content-type: application/json' \
    -d '{"application_id":"pilot-bind-1","premium":"10000.00","limit":"500000.00"}' >/dev/null
  echo "OK  BindAuthority evaluate"
fi

if curl -sf http://localhost:8105/healthz >/dev/null 2>&1; then
  python3 - <<'PY'
import json
import urllib.request

feed = json.load(urllib.request.urlopen("http://localhost:8105/trigger/feed"))
body = json.dumps({
    "event_id": "pilot-trig-1",
    "metric_value": feed["metric_value"],
    "threshold": feed["threshold"],
    "oracle_source": feed["source"],
    "oracle_payload": feed["payload"],
    "oracle_attestation_hash": feed["oracle_attestation_hash"],
    "payout_reserve": "50000.00",
}).encode()
req = urllib.request.Request(
    "http://localhost:8105/trigger/evaluate",
    data=body,
    headers={"content-type": "application/json"},
    method="POST",
)
urllib.request.urlopen(req)
PY
  echo "OK  ParametricOracle feed + evaluate"
fi

if curl -sf http://localhost:8106/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8106/audit/seal \
    -H 'content-type: application/json' \
    -d '{"claim_id":"pilot-zk-1","private_facts":{"loss_amount":"12000"}}' >/dev/null
  echo "OK  ZkClaimAudit seal"
fi

if curl -sf http://localhost:8107/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8107/spatial/evaluate \
    -H 'content-type: application/json' \
    -d '{"claim_id":"pilot-spatial-1","point_count":500000,"damage_estimate":"25000.00"}' >/dev/null
  echo "OK  SpatialTwin evaluate"
fi

if curl -sf http://localhost:8108/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8108/battery/evaluate \
    -H 'content-type: application/json' \
    -d '{"claim_id":"pilot-bat-1","state_of_health_pct":65,"thermal_event":true,"repair_estimate":"18000"}' >/dev/null
  echo "OK  BatteryLiability evaluate"
fi

if curl -sf http://localhost:8109/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8109/subrogation/evaluate \
    -H 'content-type: application/json' \
    -d '{"claim_id":"pilot-sub-1","total_loss":"100000","defendants":{"carrier_a":0.55}}' >/dev/null
  echo "OK  SubrogationGraph evaluate"
fi

if curl -sf http://localhost:8110/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8110/indemnity/evaluate \
    -H 'content-type: application/json' \
    -d '{"payment_id":"pilot-pay-crime-1","payee_name":"Acme Indemnity Trust","payee_account":"US44ACME001","amount":"50000","jurisdiction":"US"}' >/dev/null
  echo "OK  IndemnityPayGate evaluate (Crime)"
fi

if curl -sf http://localhost:8111/healthz >/dev/null 2>&1; then
  curl -sf http://localhost:8111/status?jurisdiction=UK >/dev/null
  echo "OK  ModelRiskFreeze status (E&O/Cyber)"
fi

if curl -sf http://localhost:8112/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8112/underwrite/evaluate \
    -H 'content-type: application/json' \
    -d '{"application_id":"pilot-uw-1","model_score":0.82,"jurisdiction":"UK","protected_attribute_deltas":{}}' >/dev/null
  echo "OK  UnderwritingGovern evaluate (D&O)"
fi

if curl -sf http://localhost:8113/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8113/reserve/match \
    -H 'content-type: application/json' \
    -d '{"claim_id":"pilot-rc-1","case_reserve":"100000","reinsurance_reserve":"100000","jurisdiction":"US"}' >/dev/null
  echo "OK  ReserveReconcile match"
fi

cd "$ROOT"
python3 insurance-governor/scripts/attestation_runner.py

if [[ "${ATTESTATION_CI:-}" != "1" ]]; then
  make ig-certification
  python3 insurance-governor/scripts/generate_design_partner_attestation.py
fi
echo "==> Pilot attestation complete"
