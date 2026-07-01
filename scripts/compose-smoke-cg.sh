#!/usr/bin/env bash
# Live compose smoke for CG — optional gate (requires Docker)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=compose-smoke-lib.sh
source "$ROOT/scripts/compose-smoke-lib.sh"
cd "$ROOT/cybersecurity-governor"

TOKEN="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"

echo "==> Starting CG stack (spine + egress + identity)..."
docker compose up -d --build \
  cg-postgres cg-redis cg-sidecar cg-reconciler cg-gateway cg-egress-govern cg-identity-govern

echo "==> Gateway health (8120)"
wait_for_url http://localhost:8120/readyz

echo "==> Sidecar health (8121)"
wait_for_url http://localhost:8121/readyz

echo "==> EgressGovern health (8123)"
wait_for_url http://localhost:8123/healthz

echo "==> IdentityGovern health (8124)"
wait_for_url http://localhost:8124/healthz

echo "==> governed commit"
curl -sf -X POST http://localhost:8120/governed/commit \
  -H 'content-type: application/json' \
  -d '{"platform":"egress_govern","operation_id":"smoke-cg-1","facets":{"flow_id":"smoke-cg-1","destination_host":"api.openai.com","egress_decision":"ALLOWED"},"policy_id":"egress-critical-us","reserved_budget":"0","committed_budget":"0","outcome":"allowed"}' \
  >/dev/null

echo "==> verify-chain"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8121/internal/security/verify-chain \
  | python3 "$ROOT/scripts/chain_verify_assert.py"

echo "compose-smoke-cg OK"
