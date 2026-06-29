#!/usr/bin/env bash
# fg-all-platforms-demo — exercise all five Finance Governor platforms
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
make fg-all-platforms-demo
