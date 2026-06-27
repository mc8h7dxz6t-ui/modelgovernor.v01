#!/usr/bin/env bash
# Install Python dependencies for cyber-governor unit/integration tests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m pip install --upgrade pip
python3 -m pip install \
  -r spine/sidecar/requirements.txt \
  -r spine/reconciler/requirements.txt \
  -r platforms/requirements.txt \
  -r tests/requirements-test.txt

echo ""
echo "Cyber Governor test dependencies installed."
echo "Python: $(python3 --version) ($(python3 -c 'import sys; print(sys.executable)'))"
echo "Next: make cg-spine-test"
