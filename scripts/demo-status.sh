#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

load_env
wait_for_sidecar

compose ps
compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT user_id, balance, active, lock_reason FROM user_wallets ORDER BY user_id;"
compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT trace_id, cap_amount, reserved_total, settled_total, updated_at FROM trace_budget_state ORDER BY updated_at DESC LIMIT 20;"

echo
echo "Internal wallet view (sidecar read API):"
curl -fsS "http://localhost:8081/internal/wallet/demo-user" -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN"
echo
echo
echo "Recent audit events (sidecar read API):"
curl -fsS "http://localhost:8081/internal/events/recent?limit=10" -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN"
echo
echo
echo "Observability metrics (sidecar):"
curl -fsS "http://localhost:8081/metrics" -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN"
