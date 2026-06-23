#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

require_demo_prereqs
load_env
compose up -d --build postgres redis sidecar reconciler
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
    echo "skipping already-applied migration: $filename"
    continue
  fi

  cat "$migration" | compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "INSERT INTO schema_migrations (filename) VALUES ('$filename');"
done

wait_for_sidecar

echo "demo stack is up and migrations are applied"
