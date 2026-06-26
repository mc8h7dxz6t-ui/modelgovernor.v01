#!/usr/bin/env bash
# Shared helpers for Cybersecurity Governor live demos (stack up + readiness).
set -euo pipefail

CG_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CG_DIR="${CG_DIR:-$CG_REPO_ROOT/cyber-governor}"
CG_COMPOSE_FILE="${CG_COMPOSE_FILE:-$CG_DIR/docker-compose.yml}"

cg_compose() {
  docker compose -f "$CG_COMPOSE_FILE" "$@"
}

cg_stack_detected() {
  curl -fsS "http://localhost:8103/healthz" >/dev/null 2>&1
}

cg_wait_for_url() {
  local name="$1"
  local url="$2"
  local attempts="${3:-60}"
  local i=1
  while [[ "$i" -le "$attempts" ]]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    i=$((i + 1))
  done
  echo "ERROR: timed out waiting for $name at $url" >&2
  echo "Hint: docker compose -f $CG_COMPOSE_FILE logs --tail=80" >&2
  return 1
}

cg_wait_for_stack() {
  cg_wait_for_url "cg-sidecar" "http://localhost:8101/healthz"
  cg_wait_for_url "cg-gateway" "http://localhost:8100/healthz"
  cg_wait_for_url "cg-identity-gate" "http://localhost:8103/healthz"
  cg_wait_for_url "cg-egress-lock" "http://localhost:8104/healthz"
  cg_wait_for_url "cg-witness-bridge" "http://localhost:8105/healthz"
  cg_wait_for_url "cg-lineage-ingest" "http://localhost:8106/healthz"
  cg_wait_for_url "cg-posture-reconcile" "http://localhost:8107/healthz"
  cg_wait_for_url "cg-content-guard" "http://localhost:8108/healthz"
}

ensure_cg_stack_up() {
  local skip_up="${CG_SKIP_STACK_UP:-0}"
  if cg_stack_detected; then
    return 0
  fi
  if [[ "$skip_up" == "1" ]]; then
    echo "ERROR: Cyber Governor stack is not running on :8103." >&2
    echo "Start with: make cg-stack-up   (from repo root)" >&2
    echo "         or: make -C cyber-governor cg-stack-up" >&2
    exit 1
  fi
  echo "Cyber Governor stack not detected — starting docker compose ..."
  (cd "$CG_DIR" && cg_compose up -d --build)
  cg_wait_for_stack
  echo "Cyber Governor stack is READY"
  echo ""
}
