#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-gold-lib.sh"

require_demo_prereqs
load_env
banner "ModelGovernor — starting institutional++ sales demo stack"
echo "Compose file: $COMPOSE_FILE"
echo "No API keys, cloud accounts, or service mesh required."
echo ""

compose up -d --build --force-recreate postgres redis sidecar reconciler gateway
apply_all_migrations
ensure_demo_provider_models
reset_demo_gold_state
wait_for_sidecar
wait_for_gateway
wait_for_reconciler

banner "Sales demo stack is READY"
echo "  Gateway (governed dispatch):  http://localhost:8080"
echo "  Sidecar (policy + ledger):    http://localhost:8081"
echo "  Reconciler (HA sweeps):       http://localhost:8082"
echo ""
echo "Run the full walkthrough:"
echo "  make demo-gold"
echo ""
