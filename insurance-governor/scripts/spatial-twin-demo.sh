#!/usr/bin/env bash
# SpatialTwin demo — governed spatial evidence envelope (mock vendor feed)
set -euo pipefail

URL="${SPATIAL_TWIN_URL:-http://localhost:8107}"

echo "==> SpatialTwin demo ($URL)"
curl -sf "$URL/healthz" >/dev/null
curl -sf "$URL/spatial/feed" >/dev/null
echo "OK  vendor feed"

curl -sf -X POST "$URL/spatial/evaluate" \
  -H 'content-type: application/json' \
  -d '{"claim_id":"demo-spatial-approved","point_count":500000,"bounds":{"x":1,"y":2},"damage_estimate":"15000.00","confidence":0.9}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['decision']=='APPROVED', d"

curl -sf -X POST "$URL/spatial/evaluate" \
  -H 'content-type: application/json' \
  -d '{"claim_id":"demo-spatial-held","point_count":500000,"damage_estimate":"900000.00","coverage_limit":"500000.00","confidence":0.9}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['decision']=='HELD', d"

curl -sf -X POST "$URL/spatial/evaluate" \
  -H 'content-type: application/json' \
  -d '{"claim_id":"demo-spatial-referred","point_count":500000,"damage_estimate":"10000.00","confidence":0.4}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['decision']=='REFERRED', d"

echo "spatial-twin-demo OK"
