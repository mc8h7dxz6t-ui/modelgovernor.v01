#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-gold-lib.sh"

load_env
wait_for_sidecar
reset_demo_gold_state
echo "demo-user wallet and trace budgets reset — run: make demo-gold"
