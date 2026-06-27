#!/usr/bin/env bash
# Production bootstrap: secrets + optional S3 witness bucket + deploy checklist.
#
# Usage:
#   ./scripts/cg-prod-bootstrap.sh
#   WITH_S3=1 BUCKET_NAME=corp-cg-anchors ./scripts/cg-prod-bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

WITH_S3="${WITH_S3:-0}"
BUCKET_NAME="${BUCKET_NAME:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "==> Cybersecurity Governor production bootstrap"
chmod +x scripts/bootstrap-secrets.sh

if [[ -n "$BUCKET_NAME" ]]; then
  export SECURITY_ANCHOR_S3_BUCKET="$BUCKET_NAME"
fi

./scripts/bootstrap-secrets.sh --write-env --write-k8s

if [[ "$WITH_S3" == "1" ]]; then
  if [[ -z "$BUCKET_NAME" ]]; then
    echo "ERROR: WITH_S3=1 requires BUCKET_NAME=your-globally-unique-bucket" >&2
    exit 1
  fi
  if command -v aws >/dev/null 2>&1; then
    echo "==> Provisioning S3 witness bucket via CloudFormation..."
    aws cloudformation deploy \
      --template-file deploy/infra/aws/security-anchor-bucket.yaml \
      --stack-name "cybersecuritygovernor-security-anchor-${BUCKET_NAME}" \
      --parameter-overrides "BucketName=${BUCKET_NAME}" \
      --region "$AWS_REGION" \
      --no-fail-on-empty-changeset
    echo "S3 bucket ready: ${BUCKET_NAME}"
  else
    echo "WARN: aws CLI not found — skip S3 provisioning. Deploy template manually:"
    echo "  deploy/infra/aws/security-anchor-bucket.yaml"
  fi
fi

cat <<'CHECKLIST'

==> Next steps

Staging:
  1. Upload deploy/generated/secret-manager-keys.json to your secret manager
  2. kubectl apply -k deploy/overlays/staging
  3. kubectl -n cybersecuritygovernor wait --for=condition=complete job/cg-migration --timeout=300s

Production:
  1. Add OIDC keys to secret manager (see secret-manager-keys.json placeholders)
  2. kubectl apply -k deploy/overlays/production
  3. Verify CronJobs: kubectl -n cybersecuritygovernor get cronjobs

Local docker (uses generated .env):
  docker compose --env-file .env up -d --build

Docs: PLUG-AND-PLAY.md · docs/cyber-governor/production-hardening.md

CHECKLIST
