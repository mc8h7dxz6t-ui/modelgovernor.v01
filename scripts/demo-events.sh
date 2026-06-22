#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

load_env

compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT event_id, idempotency_key, event_type, amount_delta, metadata, recorded_at FROM ledger_events ORDER BY event_id DESC LIMIT 100;"
