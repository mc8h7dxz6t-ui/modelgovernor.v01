#!/usr/bin/env bash
# Live compose smoke for ModelGovernor — gateway 8080, verify-chain (requires Docker)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.demo.yml}"

source "$ROOT/scripts/demo-gold-lib.sh"

require_demo_prereqs
load_env

echo "==> Starting MG demo stack..."
compose up -d --build postgres redis sidecar reconciler gateway
apply_all_migrations
ensure_demo_provider_models

compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
INSERT INTO user_wallets (user_id, balance, active)
VALUES ('smoke-user', 100.000000, TRUE)
ON CONFLICT (user_id) DO UPDATE SET balance = 100.000000, active = TRUE;
SQL

wait_for_sidecar
wait_for_gateway
wait_for_reconciler

TOKEN="${SIDECAR_PRIMARY_TOKEN}"
HDR=(-H "x-internal-token: $TOKEN" -H "content-type: application/json")

echo "==> Gateway health (8080)"
curl -sf http://localhost:8080/readyz

echo "==> Sidecar health (8081)"
curl -sf http://localhost:8081/readyz

echo "==> governed dispatch (reserve → settle)"
OP_KEY="smoke-$(date +%s)"
curl -sf -X POST "http://localhost:8080/governed/dispatch" \
  "${HDR[@]}" \
  -d "{\"user_id\":\"smoke-user\",\"trace_id\":\"trace-smoke\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"1.000000\",\"idempotency_key\":\"$OP_KEY\",\"prompt\":\"compose smoke\"}" \
  >/dev/null

echo "==> verify-chain"
curl -sf "http://localhost:8081/internal/ledger/verify-chain" -H "x-internal-token: $TOKEN" \
  | python3 "$ROOT/scripts/chain_verify_assert.py"

echo "compose-smoke-mg OK"
