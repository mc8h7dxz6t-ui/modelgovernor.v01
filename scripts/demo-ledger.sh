#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

load_env

compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT idempotency_key, user_id, trace_id, status, reserved_amount, actual_amount, terminal_reason, created_at, settled_at, expired_at FROM escrow_ledger ORDER BY created_at DESC LIMIT 50;"
