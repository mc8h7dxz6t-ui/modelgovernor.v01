#!/usr/bin/env bash
# Live compose smoke for CG — optional gate (requires Docker)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/cybersecurity-governor"

echo "==> Starting CG stack..."
docker compose up -d --build
sleep 8

echo "==> Gateway health (8120)"
curl -sf http://localhost:8120/readyz

echo "==> Sidecar health (8121)"
curl -sf http://localhost:8121/readyz

echo "==> EgressGovern health (8123)"
curl -sf http://localhost:8123/healthz

TOKEN="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"
echo "==> governed commit"
curl -sf -X POST http://localhost:8120/governed/commit \
  -H 'content-type: application/json' \
  -d '{"platform":"egress_govern","operation_id":"smoke-cg-1","facets":{"flow_id":"smoke-cg-1","destination_host":"api.openai.com","egress_decision":"ALLOWED"},"policy_id":"egress-critical-us","reserved_budget":"0","committed_budget":"0","outcome":"allowed"}' \
  >/dev/null

echo "==> verify-chain"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8121/internal/security/verify-chain \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d"

echo "compose-smoke-cg OK"
