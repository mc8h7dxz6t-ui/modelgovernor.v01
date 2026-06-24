#!/usr/bin/env bash
# Shared helpers for the all-platforms sales demo orchestrator.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source "$REPO_ROOT/scripts/demo-gold-lib.sh"

platform_banner() {
  local letter="$1"
  local name="$2"
  echo ""
  echo "════════════════════════════════════════════════════════════════"
  echo "  Platform $letter — $name"
  echo "════════════════════════════════════════════════════════════════"
  echo ""
}

stage_migrations_for_kustomize() {
  mkdir -p "$REPO_ROOT/deploy/base/migrations"
  cp "$REPO_ROOT"/migrations/*.sql "$REPO_ROOT/deploy/base/migrations/"
  mkdir -p "$REPO_ROOT/deploy/helm/modelgovernor/files/migrations"
  cp "$REPO_ROOT"/migrations/*.sql "$REPO_ROOT/deploy/helm/modelgovernor/files/migrations/"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

summarize_kustomize_overlay() {
  local overlay="$1"
  local label="$2"
  local outfile
  outfile="$(mktemp)"
  if ! kustomize build "$REPO_ROOT/deploy/overlays/$overlay" >"$outfile" 2>/dev/null; then
    echo "  ✗ kustomize build deploy/overlays/$overlay failed" >&2
    rm -f "$outfile"
    return 1
  fi
  local kinds deployments cronjobs
  kinds="$(grep -c '^kind:' "$outfile" || true)"
  deployments="$(grep -E '^  name: (sidecar|gateway|reconciler|pgbouncer|redis)' "$outfile" | wc -l | tr -d ' ')"
  cronjobs="$(grep -c 'kind: CronJob' "$outfile" || true)"
  echo "  ✓ $label — $kinds Kubernetes objects rendered"
  echo "    control-plane refs: $deployments | CronJobs: $cronjobs"
  grep -E 'OIDC_ENABLED|PROVIDER_MODE|LEDGER_ANCHOR|REDIS_SENTINEL|PeerAuthentication|AuthorizationPolicy' "$outfile" \
    | head -12 | sed 's/^/    /' || true
  rm -f "$outfile"
}

summarize_helm_values() {
  local values_file="$1"
  local label="$2"
  if ! have_cmd helm; then
    echo "  (skip helm — install helm to render $label)"
    return 0
  fi
  local outfile
  outfile="$(mktemp)"
  if helm template modelgovernor "$REPO_ROOT/deploy/helm/modelgovernor" \
    -f "$REPO_ROOT/deploy/helm/modelgovernor/$values_file" \
    --namespace modelgovernor >"$outfile" 2>/dev/null; then
    local lines
    lines="$(wc -l <"$outfile" | tr -d ' ')"
    echo "  ✓ Helm $label — $lines lines rendered"
    grep -E 'kind: (Deployment|CronJob|HorizontalPodAutoscaler)' "$outfile" | head -8 | sed 's/^/    /' || true
  else
    echo "  ✗ helm template failed for $values_file" >&2
  fi
  rm -f "$outfile"
}

print_platform_matrix() {
  cat <<'EOF'
  ┌──────────┬─────────────────────────────┬──────────────────┬────────────────────────────┐
  │ Platform │ SKU                         │ Live in this run │ Production flip            │
  ├──────────┼─────────────────────────────┼──────────────────┼────────────────────────────┤
  │ A        │ MG-PLATFORM-DEMO            │ make demo-gold   │ mock → live providers      │
  │ B        │ MG-PLATFORM-STAGING         │ manifest proof   │ customer VPC pilot         │
  │ C        │ MG-PLATFORM-PRODUCTION      │ manifest proof   │ Sentinel, OIDC, S3 anchor  │
  │ D        │ MG-ADDON-ENTERPRISE-SECURITY│ manifest proof   │ Istio STRICT mTLS + egress│
  └──────────┴─────────────────────────────┴──────────────────┴────────────────────────────┘

  Spec sheets: docs/sales-sheets/01-demo-platform.md … 04-enterprise-security-pack.md
  Capability matrix: docs/capability-matrix.md
EOF
}
