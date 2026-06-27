#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/cg-demo-lib.sh"

echo "==> Cybersecurity Governor — starting full stack (spine + 6 platforms)"
cg_compose up -d --build
cg_wait_for_stack
echo ""
echo "  Gateway:           http://localhost:8100"
echo "  Sidecar:           http://localhost:8101"
echo "  IdentityGate:      http://localhost:8103"
echo "  EgressLock:        http://localhost:8104"
echo "  WitnessBridge:     http://localhost:8105"
echo "  LineageIngest:     http://localhost:8106"
echo "  PostureReconcile:  http://localhost:8107"
echo "  ContentGuard:      http://localhost:8108"
echo ""
echo "Run: make cg-security-demo"
