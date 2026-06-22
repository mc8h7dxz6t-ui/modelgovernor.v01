#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

load_env
wait_for_sidecar

op_key="demo-smoke-$(date +%s)"
provider_id="provider-$op_key"

curl -fsS -X POST "http://localhost:8081/reserve" \
  -H "content-type: application/json" \
  -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"trace-smoke\",\"idempotency_key\":\"$op_key\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"10.000000\"}" >/tmp/modelgovernor-demo-smoke-reserve.json

curl -fsS -X POST "http://localhost:8081/settle" \
  -H "content-type: application/json" \
  -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" \
  -d "{\"idempotency_key\":\"$op_key\",\"outcome\":\"SETTLED\",\"actual_cost\":\"7.000000\",\"provider_request_id\":\"$provider_id\"}" >/tmp/modelgovernor-demo-smoke-settle.json

compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT user_id, balance, active, lock_reason FROM user_wallets WHERE user_id='demo-user';"
compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT idempotency_key, status, reserved_amount, actual_amount, terminal_reason FROM escrow_ledger WHERE idempotency_key='$op_key';"
compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT event_type, amount_delta, recorded_at FROM ledger_events WHERE idempotency_key='$op_key' ORDER BY event_id;"

echo "smoke demo complete for operation: $op_key"
