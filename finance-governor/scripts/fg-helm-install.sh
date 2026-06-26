#!/usr/bin/env bash
# helm upgrade --install Finance Governor (production).
set -euo pipefail

cd "$(dirname "$0")/.."
RELEASE="${FG_HELM_RELEASE:-fg}"
NAMESPACE="${FG_NAMESPACE:-finance-governor}"
CHART="./deploy/helm/finance-governor"
VALUES="${FG_HELM_VALUES:-./deploy/helm/finance-governor/values-production.yaml}"

if ! command -v helm >/dev/null 2>&1; then
  echo "helm is required: https://helm.sh/docs/intro/install/" >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required" >&2
  exit 1
fi

if [[ "${FG_BUILD_IMAGES:-false}" == "true" ]]; then
  echo "==> Building images from finance-governor spine Dockerfiles"
  REPO_ROOT="$(cd .. && pwd)"
  docker build -f spine/gateway/Dockerfile -t finance-governor-gateway:0.3.0 "$REPO_ROOT"
  docker build -f spine/sidecar/Dockerfile -t finance-governor-sidecar:0.3.0 "$REPO_ROOT"
  docker build -f spine/reconciler/Dockerfile -t finance-governor-reconciler:0.3.0 "$REPO_ROOT"
fi

# Load .env.production for --set overrides when present
SET_ARGS=()
if [[ -f .env.production ]]; then
  # shellcheck disable=SC1091
  source .env.production
  [[ -n "${OIDC_ISSUER_URL:-}" ]] && SET_ARGS+=(--set "oidc.issuerUrl=$OIDC_ISSUER_URL")
  [[ -n "${OIDC_AUDIENCE:-}" ]] && SET_ARGS+=(--set "oidc.audience=$OIDC_AUDIENCE")
  [[ -n "${DECISION_ANCHOR_S3_BUCKET:-}" ]] && SET_ARGS+=(--set "s3Anchor.bucket=$DECISION_ANCHOR_S3_BUCKET")
  [[ -n "${DECISION_ANCHOR_S3_REGION:-}" ]] && SET_ARGS+=(--set "s3Anchor.region=$DECISION_ANCHOR_S3_REGION")
  [[ "${DECISION_ANCHOR_S3_OBJECT_LOCK_ENABLED:-false}" == "true" ]] && SET_ARGS+=(--set "s3Anchor.objectLock=true")
  [[ -n "${POSTGRES_PASSWORD:-}" ]] && SET_ARGS+=(--set "postgres.password=$POSTGRES_PASSWORD")
fi

SET_ARGS+=(--set "oidc.enabled=true")
SET_ARGS+=(--set "secrets.create=false")

echo "==> helm upgrade --install $RELEASE"
helm upgrade --install "$RELEASE" "$CHART" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  -f "$VALUES" \
  "${SET_ARGS[@]}" \
  "$@"

echo "==> waiting for migrations"
kubectl -n "$NAMESPACE" wait --for=condition=complete "job/fg-migrations" --timeout=300s 2>/dev/null || \
  echo "migration job pending — check: kubectl -n $NAMESPACE get jobs"

echo "==> rollout status"
kubectl -n "$NAMESPACE" rollout status deployment/fg-sidecar --timeout=180s
kubectl -n "$NAMESPACE" rollout status deployment/fg-gateway --timeout=180s

echo ""
helm status "$RELEASE" -n "$NAMESPACE"
echo "fg-helm-install complete"
