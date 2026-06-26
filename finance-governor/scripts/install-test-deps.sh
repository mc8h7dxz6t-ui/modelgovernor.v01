#!/usr/bin/env bash
# Install Python dependencies for finance-governor unit/integration tests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m pip install --upgrade pip
python3 -m pip install \
  -r spine/sidecar/requirements.txt \
  -r spine/reconciler/requirements.txt \
  -r spine/gateway/requirements.txt \
  -r tests/requirements-test.txt

echo ""
echo "Finance Governor test dependencies installed."
echo "Python: $(python3 --version) ($(python3 -c 'import sys; print(sys.executable)'))"
echo "Next: make fg-spine-test"
