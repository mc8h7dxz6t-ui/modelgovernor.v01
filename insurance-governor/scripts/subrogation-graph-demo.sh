#!/usr/bin/env bash
# SubrogationGraph demo — governed desk evidence envelope (mock desk feed)
set -euo pipefail

URL="${SUBROGATION_GRAPH_URL:-http://localhost:8109}"

echo "==> SubrogationGraph demo ($URL)"
curl -sf "$URL/healthz" >/dev/null
curl -sf "$URL/subrogation/feed" >/dev/null
echo "OK  desk feed"

curl -sf -X POST "$URL/subrogation/evaluate" \
  -H 'content-type: application/json' \
  -d '{"claim_id":"demo-subro-recovery","total_loss":"100000.00","defendants":{"carrier_a":0.55}}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['decision']=='RECOVERY_APPROVED', d"

curl -sf -X POST "$URL/subrogation/evaluate" \
  -H 'content-type: application/json' \
  -d '{"claim_id":"demo-subro-none","total_loss":"10000.00","defendants":{}}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['decision']=='NO_RECOVERY', d"

curl -sf -X POST "$URL/subrogation/evaluate" \
  -H 'content-type: application/json' \
  -d '{"claim_id":"demo-subro-statute","total_loss":"100000.00","defendants":{"carrier_a":0.8},"statute_expired":true}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['decision']=='REFERRED', d"

echo "subrogation-graph-demo OK"
