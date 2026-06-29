#!/usr/bin/env bash
# Generate production secrets file and optional Kubernetes secret (Finance Governor standalone).
set -euo pipefail

cd "$(dirname "$0")/.."
NAMESPACE="${FG_NAMESPACE:-finance-governor}"
SECRET_NAME="${FG_SECRET_NAME:-fg-internal}"
OUT="${1:-.env.production}"

TOKEN="${FG_INTERNAL_TOKEN:-$(openssl rand -hex 32)}"
PG_PASS="${POSTGRES_PASSWORD:-$(openssl rand -hex 16)}"
OIDC_ISSUER="${OIDC_ISSUER_URL:-https://your-idp.example.com/realms/finance-governor}"
OIDC_AUD="${OIDC_AUDIENCE:-finance-governor}"
S3_BUCKET="${DECISION_ANCHOR_S3_BUCKET:-}"
S3_REGION="${DECISION_ANCHOR_S3_REGION:-us-east-1}"

cat > "$OUT" <<EOF
# Finance Governor production — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Standalone from ModelGovernor. Fill OIDC issuer from your IdP (Keycloak/Okta/Azure AD).

OIDC_ENABLED=true
OIDC_ISSUER_URL=$OIDC_ISSUER
OIDC_AUDIENCE=$OIDC_AUD
OIDC_ALLOW_INTERNAL_TOKEN_FALLBACK=false
OIDC_INTERNAL_TOKEN_IS_ADMIN=false

FG_INTERNAL_TOKEN=$TOKEN
FG_INTERNAL_TOKENS=$TOKEN
POSTGRES_PASSWORD=$PG_PASS

DECISION_ANCHOR_S3_BUCKET=$S3_BUCKET
DECISION_ANCHOR_S3_REGION=$S3_REGION
DECISION_ANCHOR_S3_PREFIX=finance-governor/decision-chain
DECISION_ANCHOR_S3_OBJECT_LOCK_ENABLED=true
DECISION_ANCHOR_S3_RETENTION_DAYS=365
EOF

echo "Wrote $OUT"

if command -v kubectl >/dev/null 2>&1; then
  kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "$NAMESPACE" create secret generic "$SECRET_NAME" \
    --from-literal=fg-internal-tokens="$TOKEN" \
    --from-literal=postgres-password="$PG_PASS" \
    --from-literal=oidc-issuer-url="$OIDC_ISSUER" \
    --from-literal=oidc-audience="$OIDC_AUD" \
    --from-literal=decision-anchor-s3-bucket="$S3_BUCKET" \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "Kubernetes secret $SECRET_NAME applied in namespace $NAMESPACE"
else
  echo "kubectl not found — apply secret manually before helm install"
fi
