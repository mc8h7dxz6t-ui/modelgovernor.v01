#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-gold-lib.sh"

load_env
compose down -v
echo "sales demo stack stopped (volumes removed — fresh wallet on next up)"
