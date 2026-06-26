#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/cg-demo-lib.sh"

echo "==> Resetting Cyber Governor stack (removes Postgres volume)"
cg_compose down -v --remove-orphans
echo "==> Rebuilding and starting full stack"
cg_compose up -d --build --wait --wait-timeout "${CG_COMPOSE_WAIT_TIMEOUT:-300}"
cg_wait_for_stack
echo "cg-stack-reset OK"
