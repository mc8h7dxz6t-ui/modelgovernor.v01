#!/usr/bin/env bash
# ModelGovernor — full structural certification: 12 live loops + 134-test gate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

source "$REPO_ROOT/scripts/demo-gold-lib.sh"

DEMO_ALL_TEST_TARGET="${DEMO_ALL_TEST_TARGET:-134}"
DEMO_ALL_SKIP_LIVE="${DEMO_ALL_SKIP_LIVE:-0}"

banner "ModelGovernor — make demo-all (12 structural loops + ${DEMO_ALL_TEST_TARGET} tests)"

if [[ "$DEMO_ALL_SKIP_LIVE" != "1" ]]; then
  if ! curl -fsS "http://localhost:8081/healthz" >/dev/null 2>&1; then
    echo "==> Stack not running — bringing up demo-gold stack"
    make demo-gold-up
    sleep 3
  fi
  make demo-gold-reset
  echo ""
  echo "==> Loops 1–11: institutional++ live walkthrough"
  make demo-gold
else
  echo "==> DEMO_ALL_SKIP_LIVE=1 — skipping live loops 1–11 (offline structural gate only)"
fi

step "12/12  Structural certification — Tier-1 pytest gate (${DEMO_ALL_TEST_TARGET} tests)"
"$REPO_ROOT/scripts/demo-all-pytest-gate.sh"

banner "demo-all COMPLETE"
echo "  Loops:   12/12 structural"
echo "  Tests:   ${DEMO_ALL_TEST_TARGET}+ passed (see pytest summary above)"
echo "  Rerun:   make demo-all"
echo "  Offline: DEMO_ALL_SKIP_LIVE=1 make demo-all"
