#!/usr/bin/env bash
# Shared helpers for the institutional++ sales demo stack.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export COMPOSE_FILE="${COMPOSE_FILE:-$REPO_ROOT/docker-compose.demo.yml}"

source "$REPO_ROOT/scripts/demo-lib.sh"

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
WHERE trace_id IN ('trace-gold', 'trace-multi') OR trace_id LIKE 'trace-gold-%';
SQL
  curl -fsS -X POST "http://localhost:8081/internal/diagnostic/clear" \
    -H "x-internal-token: ${SIDECAR_PRIMARY_TOKEN}" >/dev/null 2>&1 || true
  redis_cli DEL mg:diagnostic_mode >/dev/null 2>&1 || true
}
