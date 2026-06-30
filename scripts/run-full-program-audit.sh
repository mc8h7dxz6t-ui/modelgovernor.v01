#!/usr/bin/env bash
# Full cross-platform test + conformance audit — head-of-engineering gate
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPORT_DIR="$ROOT/artifacts/full-program-audit"
mkdir -p "$REPORT_DIR"
SUMMARY="$REPORT_DIR/summary.json"
LOG="$REPORT_DIR/run.log"
: >"$LOG"

pass=0
fail=0
skip=0
results=()

record() {
  local name="$1" status="$2" detail="${3:-}"
  results+=("{\"name\":\"$name\",\"status\":\"$status\",\"detail\":\"$detail\"}")
  if [[ "$status" == "PASS" ]]; then pass=$((pass + 1)); elif [[ "$status" == "SKIP" ]]; then skip=$((skip + 1)); else fail=$((fail + 1)); fi
  echo "[$status] $name ${detail:+- $detail}" | tee -a "$LOG"
}

run_step() {
  local name="$1"
  shift
  local out="$REPORT_DIR/$(echo "$name" | tr ' /' '__').log"
  echo "=== $name ===" >>"$LOG"
  if "$@" >"$out" 2>&1; then
    record "$name" "PASS" "$(tail -1 "$out" 2>/dev/null || true)"
  else
    record "$name" "FAIL" "see $(basename "$out")"
  fi
}

echo "Full program audit started $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

# --- Kernel static conformance ---
run_step "kernel-K1-ledger-registry" \
  env PYTHONPATH=governor-spine-core python3 -c "
from pathlib import Path
from spine_core.ledger_registry import conformance_failures
assert conformance_failures(Path('.')) == []
print('K1 OK')
"

run_step "kernel-K3-sweep-seal" \
  env PYTHONPATH=governor-spine-core python3 -c "
from pathlib import Path
from spine_core.sweep_seal import sweep_conformance_failures
assert sweep_conformance_failures(Path('.')) == []
print('K3 OK')
"

run_step "kernel-H1-append-lock" \
  env PYTHONPATH=governor-spine-core python3 -c "
from pathlib import Path
from spine_core.append_lock import append_lock_conformance_failures
assert append_lock_conformance_failures(Path('.')) == []
print('H1 OK')
"

run_step "kernel-K4-retention-cronjob" \
  env PYTHONPATH=governor-spine-core python3 -c "
from pathlib import Path
from spine_core.retention_cronjob import retention_cronjob_conformance_failures
assert retention_cronjob_conformance_failures(Path('.')) == []
print('K4 OK')
"

run_step "kernel-M1-spine-consolidation" \
  env PYTHONPATH=governor-spine-core python3 -c "
from pathlib import Path
from spine_core.m1_conformance import m1_conformance_failures
assert m1_conformance_failures(Path('.')) == []
print('M1 OK')
"

run_step "kernel-port-alignment" \
  env PYTHONPATH=governor-spine-core python3 -c "
from spine_core.port_checks import port_alignment_failures
assert port_alignment_failures() == []
print('ports OK')
"

# --- Spine-core unit tests ---
run_step "spine-core-all-tests" \
  env PYTHONPATH=governor-spine-core python3 -m pytest governor-spine-core/tests/ -q --tb=no

# --- ModelGovernor ---
run_step "MG-integration-hardening" \
  env PYTHONPATH=governor-spine-core:. python3 -m pytest \
    tests/integration/test_ledger_hardening.py \
    tests/integration/test_ledger_seal_failclosed.py -q --tb=no

run_step "MG-L4-certification-ci" make mg-certification-l4-ci

# --- Finance Governor ---
run_step "FG-spine-unit-tests" make -C finance-governor fg-spine-test

run_step "FG-L4-certification-ci" make -C finance-governor fg-certification-l4-ci

# --- Insurance Governor ---
run_step "IG-spine-unit-tests" make -C insurance-governor ig-spine-test

run_step "IG-L4-certification-ci" make -C insurance-governor ig-certification-l4-ci

# --- Cybersecurity Governor ---
run_step "CG-spine-unit-tests" make -C cybersecurity-governor cg-spine-test

run_step "CG-L4-certification-ci" make -C cybersecurity-governor cg-certification-l4-ci

run_step "CG-property-security-chain" make -C cybersecurity-governor cg-property-test

# --- Portfolio plug (L5 self-check) ---
run_step "portfolio-il-rubric" \
  env PYTHONPATH=governor-spine-core python3 -c "
from pathlib import Path
from spine_core.il_rubric import evaluate_portfolio, ENGINEERING_CEILING
r = evaluate_portfolio(Path('.'))
assert r['portfolio_engineering_score'] >= 7.0
print(f'IL rubric OK engineering={r[\"portfolio_engineering_score\"]}/{ENGINEERING_CEILING}')
"

run_step "portfolio-plug-artifact" make plug

# --- Helm K4 retention ---
run_step "helm-K4-retention-MG" \
  bash -c "helm template deploy/helm/modelgovernor 2>/dev/null | grep -qi ledger-retention"

run_step "helm-K4-retention-FG" \
  bash -c "helm template finance-governor/deploy/helm/finance-governor 2>/dev/null | grep -qi decision-retention"

run_step "helm-K4-retention-IG" \
  bash -c "helm template deploy/helm/insurancegovernor 2>/dev/null | grep -qi ledger-retention"

run_step "helm-K4-retention-CG" \
  bash -c "helm template deploy/helm/cybersecuritygovernor 2>/dev/null | grep -qi ledger-retention"

# --- Write summary JSON ---
{
  echo "{"
  echo "  \"generated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"git_sha\": \"$(git rev-parse HEAD 2>/dev/null || echo unknown)\","
  echo "  \"passed\": $pass,"
  echo "  \"failed\": $fail,"
  echo "  \"skipped\": $skip,"
  echo "  \"results\": ["
  for i in "${!results[@]}"; do
    sep=","
    [[ $i -eq $((${#results[@]} - 1)) ]] && sep=""
    echo "    ${results[$i]}$sep"
  done
  echo "  ]"
  echo "}"
} >"$SUMMARY"

echo "" | tee -a "$LOG"
echo "FULL PROGRAM AUDIT: $pass passed, $fail failed, $skip skipped" | tee -a "$LOG"
echo "Summary: $SUMMARY" | tee -a "$LOG"
exit $([[ $fail -eq 0 ]] && echo 0 || echo 1)
