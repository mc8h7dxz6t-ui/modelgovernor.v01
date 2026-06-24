#!/usr/bin/env bash
# Shared helpers for the institutional++ sales demo stack.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export COMPOSE_FILE="${COMPOSE_FILE:-$REPO_ROOT/docker-compose.demo.yml}"

source "$REPO_ROOT/scripts/demo-lib.sh"

# Stay at/below sidecar default manual_approval_cost_threshold (2.000000) so the demo
# works even if compose env was not reapplied after a git pull.
export DEMO_RESERVE_COST="${DEMO_RESERVE_COST:-2.000000}"
export DEMO_DRIFT_RESERVE_COST="${DEMO_DRIFT_RESERVE_COST:-2.000000}"
export DEMO_DRIFT_ACTUAL_COST="${DEMO_DRIFT_ACTUAL_COST:-4.500000}"

compose() {
  (cd "$REPO_ROOT" && docker compose -f "$COMPOSE_FILE" "$@")
}

banner() {
  echo ""
  echo "════════════════════════════════════════════════════════════════"
  echo "  $*"
  echo "════════════════════════════════════════════════════════════════"
  echo ""
}

step() {
  echo ""
  echo "▶ $*"
  echo "────────────────────────────────────────────────────────────────"
}

wait_for_gateway() {
  local retries=45
  for ((i=1; i<=retries; i++)); do
    if curl -fsS "http://localhost:8080/healthz" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "gateway did not become healthy in time" >&2
  return 1
}

wait_for_reconciler() {
  local retries=45
  for ((i=1; i<=retries; i++)); do
    if curl -fsS "http://localhost:8082/healthz" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "reconciler did not become healthy in time" >&2
  return 1
}

redis_cli() {
  if command -v redis-cli >/dev/null 2>&1; then
    redis-cli -h localhost "$@"
  else
    compose exec -T redis redis-cli "$@"
  fi
}

apply_all_migrations() {
  wait_for_postgres
  compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
SQL

  for migration in "$REPO_ROOT"/migrations/*.sql; do
    filename="$(basename "$migration")"
    already_applied="$(compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1 FROM schema_migrations WHERE filename = '$filename' LIMIT 1;")"
    if [[ "$already_applied" == "1" ]]; then
      echo "  ✓ migration already applied: $filename"
      continue
    fi
    echo "  → applying $filename"
    cat "$migration" | compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
    compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "INSERT INTO schema_migrations (filename) VALUES ('$filename');"
  done
}

reset_demo_gold_state() {
  echo "Resetting demo-user wallet, trace budgets, and diagnostic flags..."
  compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
INSERT INTO user_wallets (user_id, balance, active)
VALUES ('demo-user', 100.000000, TRUE)
ON CONFLICT (user_id) DO UPDATE
SET balance = 100.000000,
    active = TRUE,
    lock_reason = NULL,
    locked_at = NULL;
DELETE FROM trace_budget_state
WHERE trace_id IN ('trace-gold', 'trace-multi', 'trace-idem', 'trace-circuit', 'trace-redis-fallback')
   OR trace_id LIKE 'trace-gold-%'
   OR trace_id LIKE 'trace-drift%';
DELETE FROM budget_scope_state
WHERE (scope_type = 'user' AND scope_key = 'demo-user')
   OR (scope_type = 'tenant' AND scope_key = 'default-tenant')
   OR (scope_type = 'session' AND scope_key = 'default-session')
   OR (scope_type = 'run' AND scope_key = 'default-agent-run');
DELETE FROM ledger_events
WHERE idempotency_key LIKE 'gold-idem-%'
   OR idempotency_key LIKE 'gold-drift-%'
   OR idempotency_key LIKE 'demo-drift-%'
   OR idempotency_key LIKE 'demo-post-lock%'
   OR idempotency_key LIKE 'gold-circuit-%'
   OR idempotency_key LIKE 'gold-fallback-%';
DELETE FROM provider_dispatch_attempts
WHERE idempotency_key LIKE 'gold-idem-%'
   OR idempotency_key LIKE 'gold-drift-%'
   OR idempotency_key LIKE 'demo-drift-%'
   OR idempotency_key LIKE 'demo-post-lock%'
   OR idempotency_key LIKE 'gold-circuit-%'
   OR idempotency_key LIKE 'gold-fallback-%';
DELETE FROM execution_lineage
WHERE idempotency_key LIKE 'gold-idem-%'
   OR idempotency_key LIKE 'gold-drift-%'
   OR idempotency_key LIKE 'demo-drift-%'
   OR idempotency_key LIKE 'demo-post-lock%'
   OR idempotency_key LIKE 'gold-circuit-%'
   OR idempotency_key LIKE 'gold-fallback-%';
DELETE FROM escrow_ledger
WHERE idempotency_key LIKE 'gold-idem-%'
   OR idempotency_key LIKE 'gold-drift-%'
   OR idempotency_key LIKE 'demo-drift-%'
   OR idempotency_key LIKE 'demo-post-lock%'
   OR idempotency_key LIKE 'gold-circuit-%'
   OR idempotency_key LIKE 'gold-fallback-%';
SQL
  clear_provider_circuit "gpt-4o-mini"
  curl -fsS -X POST "http://localhost:8081/internal/diagnostic/clear" \
    -H "x-internal-token: ${SIDECAR_PRIMARY_TOKEN}" >/dev/null 2>&1 || true
  redis_cli DEL mg:diagnostic_mode >/dev/null 2>&1 || true
}

clear_provider_circuit() {
  local model="${1:-gpt-4o-mini}"
  redis_cli DEL "mg:circuit:${model}:open" "mg:circuit:${model}:failures" >/dev/null 2>&1 || true
}

open_provider_circuit() {
  local model="${1:-gpt-4o-mini}"
  redis_cli SET "mg:circuit:${model}:open" 1 EX 120 >/dev/null 2>&1
}

ensure_redis_up() {
  compose start redis >/dev/null 2>&1 || true
  local retries=15
  for ((i=1; i<=retries; i++)); do
    if redis_cli ping >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "redis did not become ready in time" >&2
  return 1
}

curl_post_expect() {
  local label="$1"
  local expected="${2:-200}"
  local url="$3"
  shift 3
  local body_file
  body_file="$(mktemp)"
  local status
  status="$(curl -sS -o "$body_file" -w "%{http_code}" -X POST "$url" "$@")"
  if [[ "$status" != "$expected" ]]; then
    echo "ERROR: $label failed with HTTP $status (expected $expected)" >&2
    cat "$body_file" >&2
    echo "" >&2
    rm -f "$body_file"
    return 1
  fi
  cat "$body_file"
  rm -f "$body_file"
}

preflight_demo_gold() {
  echo "Preflight: verifying demo-user wallet and sidecar policy thresholds..."
  local wallet threshold gateway_token sidecar_tokens
  wallet="$(curl -fsS "http://localhost:8081/internal/wallet/demo-user" \
    -H "x-internal-token: ${SIDECAR_PRIMARY_TOKEN}")"
  threshold="$(compose exec -T sidecar printenv MANUAL_APPROVAL_COST_THRESHOLD 2>/dev/null || echo "unset")"
  gateway_token="$(compose exec -T gateway printenv SIDECAR_INTERNAL_TOKEN 2>/dev/null || echo "unset")"
  sidecar_tokens="$(compose exec -T sidecar printenv SIDECAR_INTERNAL_TOKENS 2>/dev/null || echo "unset")"
  echo "$wallet" | python3 -m json.tool 2>/dev/null || echo "$wallet"
  echo "  sidecar MANUAL_APPROVAL_COST_THRESHOLD=${threshold:-unset}"
  echo "  gateway SIDECAR_INTERNAL_TOKEN=${gateway_token:-unset}"
  echo "  sidecar SIDECAR_INTERNAL_TOKENS=${sidecar_tokens:-unset}"
  echo "  demo reserve amount=${DEMO_RESERVE_COST}"
  local active
  active="$(echo "$wallet" | python3 -c "import sys,json; print(json.load(sys.stdin).get('active', False))" 2>/dev/null || echo "false")"
  if [[ "$active" != "True" && "$active" != "true" ]]; then
    echo "ERROR: demo-user wallet is inactive/locked — run: make demo-gold-reset" >&2
    return 1
  fi
  if [[ "${gateway_token%%$'\r'}" != "${SIDECAR_PRIMARY_TOKEN}" ]]; then
    echo "WARN: gateway token may not match shell token — recreate stack: make demo-gold-down && make demo-gold-up" >&2
  fi
}
