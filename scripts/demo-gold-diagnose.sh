#!/usr/bin/env bash
# Quick diagnostics when demo-gold returns HTTP 409 or auth errors.
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-gold-lib.sh"

load_env
banner "ModelGovernor demo-gold diagnostics"

preflight_demo_gold || true

echo ""
echo "Probe governed dispatch (should return 200):"
set +e
curl_post_expect "governed dispatch probe" 200 "http://localhost:8080/governed/dispatch" \
  -H "x-internal-token: ${SIDECAR_PRIMARY_TOKEN}" \
  -H "content-type: application/json" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"diag-$(date +%s)\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"${DEMO_RESERVE_COST}\",\"idempotency_key\":\"diag-$(date +%s)\",\"prompt\":\"diag\"}" \
  | python3 -m json.tool 2>/dev/null
probe_status=$?
set -e

if [[ "$probe_status" -ne 0 ]]; then
  echo ""
  echo "If detail mentions 'manual approval': recreate sidecar after git pull:"
  echo "  docker compose -f docker-compose.demo.yml up -d --force-recreate sidecar gateway"
  echo "Or reset state:"
  echo "  make demo-gold-reset"
  exit 1
fi

echo ""
echo "Diagnostics OK — run: make demo-gold"
