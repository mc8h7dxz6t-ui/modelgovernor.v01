#!/usr/bin/env bash
# Collated demo across Platform A (live) + B/C/D (manifest proof) + optional engineering proof.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/scripts/demo-all-platforms-lib.sh"

RUN_LIVE=1
RUN_MANIFESTS=1
RUN_PROOF=0
SKIP_GOLD_UP=0

usage() {
  cat <<'EOF'
Usage: demo-all-platforms.sh [options]

  --live-only        Run Platform A (make demo-gold) only
  --manifests-only   Render B/C/D overlays only (no live Docker demo)
  --with-proof       Also run make proof-test (Postgres invariant suite)
  --skip-gold-up     Do not auto-start demo stack if down (fail with hint)
  -h, --help         Show this help

Default: live Platform A + manifest proof for B, C, D.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --live-only) RUN_MANIFESTS=0 ;;
    --manifests-only) RUN_LIVE=0 ;;
    --with-proof) RUN_PROOF=1 ;;
    --skip-gold-up) SKIP_GOLD_UP=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

banner "ModelGovernor — ALL PLATFORMS collated demo"
echo "Platforms A–D: sales demo → staging pilot → production institutional++ → enterprise security"
echo ""
print_platform_matrix

if [[ "$RUN_MANIFESTS" -eq 1 ]]; then
  platform_banner "B" "Staging / Pilot (MG-PLATFORM-STAGING)"
  echo "Deploy path: kubectl apply -k deploy/overlays/staging"
  echo "Helm path:   helm install modelgovernor deploy/helm/modelgovernor -f values-staging.yaml"
  echo ""
  if have_cmd kustomize; then
    stage_migrations_for_kustomize
    summarize_kustomize_overlay "staging" "Kustomize staging overlay"
    summarize_helm_values "values-staging.yaml" "values-staging.yaml"
  else
    echo "  Install kustomize to render manifests locally (CI validates on every merge)."
    echo "  https://kubectl.docs.kubernetes.io/installation/kustomize/"
  fi
  echo "  Sales point: live providers + GitOps pilot in buyer VPC — 2+ sidecar replicas, HPA"

  platform_banner "C" "Production Institutional++ (MG-PLATFORM-PRODUCTION)"
  echo "Deploy path: kubectl apply -k deploy/overlays/production"
  echo "Includes: Redis Sentinel, dual OIDC, S3 Object Lock anchor, governance CronJobs"
  echo ""
  if have_cmd kustomize; then
    summarize_kustomize_overlay "production" "Kustomize production overlay"
    summarize_helm_values "values-production.yaml" "values-production.yaml"
  fi
  echo "  Sales point: regulated-enterprise control plane — ledger hash chain + hourly verify + anchor"

  platform_banner "D" "Enterprise Security Pack (MG-ADDON-ENTERPRISE-SECURITY)"
  echo "Deploy path: included in production overlay; base at deploy/overlays/enterprise"
  echo ""
  if have_cmd kustomize; then
    summarize_kustomize_overlay "enterprise" "Kustomize enterprise Istio overlay"
  fi
  echo "  Sales point: STRICT mTLS mesh + LLM egress allowlist (OpenAI, Anthropic)"
fi

if [[ "$RUN_LIVE" -eq 1 ]]; then
  platform_banner "A" "Sales Demo — LIVE (MG-PLATFORM-DEMO)"
  echo "Stack: docker-compose.demo.yml | Command: make demo-gold (11 steps)"
  echo ""

  if ! curl -fsS "http://localhost:8081/healthz" >/dev/null 2>&1; then
    if [[ "$SKIP_GOLD_UP" -eq 1 ]]; then
      echo "ERROR: demo stack is not running. Start with: make demo-gold-up" >&2
      exit 1
    fi
    echo "Demo stack not detected — starting with make demo-gold-up ..."
    "$REPO_ROOT/scripts/demo-gold-up.sh"
  fi

  "$REPO_ROOT/scripts/demo-gold.sh"
fi

if [[ "$RUN_PROOF" -eq 1 ]]; then
  platform_banner "∎" "Engineering proof plane (institutional++ invariants)"
  echo "Running Postgres vigorous invariant suite (make proof-test) ..."
  make -C "$REPO_ROOT" proof-test
  echo "  Sales point: same invariants enforced in CI Tier 2 — not slide-ware"
fi

banner "ALL PLATFORMS DEMO COMPLETE"
cat <<'EOF'
  Next steps for buyers:
    A → already live (Docker mock) — flip PROVIDER_MODE=live for pilot
    B → deploy/overlays/staging + ExternalSecrets + provider API keys
    C → deploy/overlays/production + S3 anchor bucket + IdP
    D → enterprise Istio overlay (included in C; optional hardening review)

  Teardown live stack: make demo-gold-down
  Rerun live only:     make demo-gold-reset && make demo-gold
  Manifests only:      make demo-all-platforms-manifests
EOF
