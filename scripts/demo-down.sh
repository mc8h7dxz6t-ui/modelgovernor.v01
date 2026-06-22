#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

compose down

echo "demo stack stopped"
