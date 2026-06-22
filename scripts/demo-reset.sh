#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-lib.sh"

compose down -v
"$REPO_ROOT/scripts/demo-up.sh"
