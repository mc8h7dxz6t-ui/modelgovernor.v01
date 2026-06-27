#!/usr/bin/env bash
# Run institutional++ reliability steps (7–12) after the core demo stack is up.
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-gold-lib.sh"

load_env
wait_for_sidecar
wait_for_reconciler
ensure_redis_up

TOKEN="${SIDECAR_PRIMARY_TOKEN}"
HDR=(-H "x-internal-token: $TOKEN" -H "content-type: application/json")

banner "ModelGovernor — institutional++ reliability drill (steps 7–12)"
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/demo-gold-reliability.sh"

echo ""
echo "Reliability drill complete. Reset wallet for another run: make demo-gold-reset"
