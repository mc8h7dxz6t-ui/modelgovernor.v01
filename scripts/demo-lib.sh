#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

require_demo_prereqs() {
  if ! "$REPO_ROOT/scripts/install-demo-prereqs.sh" --check-only >/dev/null 2>&1; then
    echo "Demo prerequisites missing (Docker, Docker Compose, curl, make)." >&2
    echo "Install from bash:" >&2
    echo "  make demo-prereqs-install" >&2
    echo "  # or: ./scripts/install-demo-prereqs.sh --install" >&2
    "$REPO_ROOT/scripts/install-demo-prereqs.sh" --check-only >&2 || true
    exit 1
  fi
}

compose() {
  (cd "$REPO_ROOT" && docker compose "$@")
}

ensure_env_file() {
  if [[ ! -f "$REPO_ROOT/.env" ]]; then
    cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  fi
}

load_env() {
  ensure_env_file
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a

  export POSTGRES_DB="${POSTGRES_DB:-modelgovernor}"
  export POSTGRES_USER="${POSTGRES_USER:-postgres}"
  export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
  export SIDECAR_INTERNAL_TOKENS="${SIDECAR_INTERNAL_TOKENS:-dev-sidecar-token}"
  export SIDECAR_PRIMARY_TOKEN="${SIDECAR_INTERNAL_TOKENS%%,*}"
}

wait_for_sidecar() {
  local retries=45
  local wait_seconds=2

  for ((i=1; i<=retries; i++)); do
    if curl -fsS "http://localhost:8081/healthz" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$wait_seconds"
  done

  echo "sidecar did not become healthy in time" >&2
  return 1
}

wait_for_postgres() {
  local retries=45
  local wait_seconds=2

  for ((i=1; i<=retries; i++)); do
    if compose exec -T postgres sh -c "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\"" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$wait_seconds"
  done

  echo "postgres did not become ready in time" >&2
  return 1
}
