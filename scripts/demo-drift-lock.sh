#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

load_env
wait_for_sidecar

op_key="demo-drift-$(date +%s)"
provider_id="provider-$op_key"

curl -fsS -X POST "http://localhost:8081/reserve" \
  -H "content-type: application/json" \
  -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"trace-drift\",\"idempotency_key\":\"$op_key\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"10.000000\"}" >/tmp/modelgovernor-demo-drift-reserve.json

curl -fsS -X POST "http://localhost:8081/settle" \
  -H "content-type: application/json" \
  -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" \
  -d "{\"idempotency_key\":\"$op_key\",\"outcome\":\"SETTLED\",\"actual_cost\":\"12.000000\",\"provider_request_id\":\"$provider_id\"}" >/tmp/modelgovernor-demo-drift-settle.json

status_code="$(curl -sS -o /tmp/modelgovernor-demo-drift-post-lock.json -w "%{http_code}" -X POST "http://localhost:8081/reserve" \
  -H "content-type: application/json" \
  -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" \
  -d '{"user_id":"demo-user","trace_id":"trace-drift-post-lock","idempotency_key":"demo-post-lock","model":"gpt-4o-mini","estimated_cost":"1.000000"}')"

if [[ "$status_code" != "409" ]]; then
  echo "expected post-lock reserve to fail with HTTP 409, got $status_code" >&2
  exit 1
fi

compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT user_id, balance, active, lock_reason, locked_at FROM user_wallets WHERE user_id='demo-user';"
compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT event_type, amount_delta, metadata FROM ledger_events WHERE idempotency_key='$op_key' ORDER BY event_id;"

echo "drift-lock demo complete for operation: $op_key"
