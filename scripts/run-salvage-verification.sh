#!/usr/bin/env bash
# Portfolio salvage verification — institutional self-check (not third-party certification)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[ CLEANUP ] Checking for stale cyber-governor tree..."
if [[ -d cyber-governor ]]; then
  echo "FAIL: legacy cyber-governor/ still present"
  exit 1
fi
echo "OK    no legacy cyber-governor/ tree"

echo "[ MANIFEST ] governor-spine-core domain registry..."
PYTHONPATH=governor-spine-core python3 -m pytest governor-spine-core/tests/ -q

echo "[ INTEGRITY ] CG spine tests (offline)..."
make -C cybersecurity-governor cg-spine-test

echo "[ INTEGRITY ] FG unit tests..."
make -C finance-governor fg-spine-test 2>/dev/null || (
  cd "$ROOT" && PYTHONPATH=finance-governor/spine/sidecar:finance-governor/tests:finance-governor \
    python3 -m pytest finance-governor/tests/ -q --ignore=finance-governor/tests/chaos --ignore=finance-governor/tests/load
)

echo "[ INTEGRITY ] MG tier-1 subset..."
cd "$ROOT" && python3 -m pytest tests/integration/test_reserve_settle.py tests/integration/test_hash_chain.py -q 2>/dev/null || \
  python3 -m pytest tests/integration/ -q --maxfail=3

echo "[ SMOKE ] Helm template renders (CG)..."
make -C cybersecurity-governor cg-helm-enterprise > /dev/null

echo "[ SMOKE ] Port alignment (FG/IG/CG Dockerfiles vs compose)..."
PYTHONPATH=governor-spine-core python3 -c "
from spine_core.port_checks import port_alignment_failures
f = port_alignment_failures()
assert not f, chr(10).join(f)
print('OK    spine ports aligned')
"

echo "[ STATUS ] Institutional Self-Check Certified (pytest + port alignment + helm render)"
echo "Note: this is NOT third-party L5 certification. Live compose smoke is a separate gate."
