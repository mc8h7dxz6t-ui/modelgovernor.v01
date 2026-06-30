#!/usr/bin/env bash
# Wrapper for image promotion — build/tag/push governor container images.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/promote-images.py" "$@"
