#!/usr/bin/env bash
# Create Finance Governor S3 decision-chain anchor bucket (Object Lock).
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${FG_ANCHOR_STACK_NAME:-fg-decision-anchor}"
BUCKET_NAME="${DECISION_ANCHOR_S3_BUCKET:-}"

if [[ -z "$BUCKET_NAME" ]]; then
  BUCKET_NAME="fg-decision-anchor-$(openssl rand -hex 4)"
  echo "Generated bucket name: $BUCKET_NAME"
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI required" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$SCRIPT_DIR/../deploy/infra/aws/decision-anchor-bucket.yaml"

aws cloudformation deploy \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE" \
  --parameter-overrides "BucketName=$BUCKET_NAME" \
  --no-fail-on-empty-changeset

echo "DECISION_ANCHOR_S3_BUCKET=$BUCKET_NAME"
echo "DECISION_ANCHOR_S3_REGION=$REGION"
echo "Export these in .env.production or Kubernetes secret decision-anchor-s3-bucket"
