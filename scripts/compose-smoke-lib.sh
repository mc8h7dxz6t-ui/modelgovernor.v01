#!/usr/bin/env bash
# Shared helpers for governor compose-smoke scripts.
set -euo pipefail

wait_for_url() {
  local url=$1
  local retries=${2:-45}
  for ((i = 1; i <= retries; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "timeout waiting for $url" >&2
  return 1
}
