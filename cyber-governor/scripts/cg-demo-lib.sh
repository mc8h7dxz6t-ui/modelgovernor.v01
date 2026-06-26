#!/usr/bin/env bash
# Shared helpers for Cybersecurity Governor live demos (stack up + readiness).
set -euo pipefail

CG_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CG_DIR="${CG_DIR:-$CG_REPO_ROOT/cyber-governor}"
CG_COMPOSE_FILE="${CG_COMPOSE_FILE:-$CG_DIR/docker-compose.yml}"
CG_WAIT_ATTEMPTS="${CG_WAIT_ATTEMPTS:-90}"
CG_COMPOSE_WAIT_TIMEOUT="${CG_COMPOSE_WAIT_TIMEOUT:-300}"

cg_compose() {
  docker compose -f "$CG_COMPOSE_FILE" "$@"
}

cg_stack_detected() {
  curl -fsS "http://localhost:8103/healthz" >/dev/null 2>&1 \
    && curl -fsS "http://localhost:8108/healthz" >/dev/null 2>&1
}

cg_http_healthcheck() {
  local port="$1"
  python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${port}/healthz', timeout=2)"
}

cg_wait_for_url() {
  local name="$1"
  local url="$2"
  local attempts="${3:-$CG_WAIT_ATTEMPTS}"
  local i=1
  echo "  waiting for $name ..."
  while [[ "$i" -le "$attempts" ]]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "  $name ready"
      return 0
    fi
    if (( i % 10 == 0 )); then
      echo "  still waiting for $name (${i}/${attempts}) ..."
    fi
    sleep 2
    i=$((i + 1))
  done
  echo "ERROR: timed out waiting for $name at $url" >&2
  cg_diagnose_stack "$name"
  return 1
}

cg_diagnose_stack() {
  local failed="${1:-unknown}"
  echo "" >&2
  echo "=== Cyber Governor stack diagnostics (failed: $failed) ===" >&2
  cg_compose ps -a >&2 || true
  echo "" >&2
  for svc in cg-identity-gate cg-sidecar cg-postgres cg-posture-reconcile cg-content-guard; do
    echo "--- logs: $svc (last 40 lines) ---" >&2
    cg_compose logs --no-color --tail=40 "$svc" 2>&1 >&2 || true
    echo "" >&2
  done
  echo "Recovery options:" >&2
  echo "  make cg-stack-reset     # down -v, rebuild, wait (fixes stale Postgres volume)" >&2
  echo "  lsof -i :8103           # check for host port conflict on Mac" >&2
  echo "  CG_SKIP_STACK_UP=1 make cg-security-demo  # fail fast if stack should already be up" >&2
}

cg_wait_for_stack() {
  cg_wait_for_url "cg-sidecar" "http://localhost:8101/readyz"
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
  echo "Cyber Governor stack not detected — starting docker compose (first run may take a few minutes) ..."
  (cd "$CG_DIR" && cg_compose up -d --build --wait --wait-timeout "$CG_COMPOSE_WAIT_TIMEOUT") || {
    echo "WARN: compose --wait exited non-zero; checking endpoints ..." >&2
  }
  if ! cg_wait_for_stack; then
    echo "Retrying platform containers once with --force-recreate ..." >&2
    (cd "$CG_DIR" && cg_compose up -d --build --force-recreate \
      cg-identity-gate cg-egress-lock cg-witness-bridge cg-lineage-ingest \
      cg-posture-reconcile cg-content-guard) || true
    cg_wait_for_stack
  fi
  echo "Cyber Governor stack is READY"
  echo ""
}
