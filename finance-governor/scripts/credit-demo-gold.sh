#!/usr/bin/env bash
# CreditGovern — demo-ready walkthrough (reserve-before-score)
set -euo pipefail

CREDIT="${CREDITGOVERN_URL:-http://localhost:8097}"

echo "==> CreditGovern institutional++ demo"
echo ""
echo "1) Health"
curl -sf "$CREDIT/healthz"
echo ""

echo "2) Approved model — low exposure APPROVE"
curl -sf -X POST "$CREDIT/credit/evaluate" \
  -H 'content-type: application/json' \
  -d '{"application_id":"demo-approve","exposure_amount":"50000.00","model_version_id":"credit-model-v3","desk_id":"desk-default"}'
echo ""

echo "3) Unapproved model version — BLOCKED"
curl -sf -X POST "$CREDIT/credit/evaluate" \
  -H 'content-type: application/json' \
  -d '{"application_id":"demo-blocked","exposure_amount":"25000.00","model_version_id":"credit-model-v99","desk_id":"desk-default"}'
echo ""

echo "4) High exposure — REFER"
curl -sf -X POST "$CREDIT/credit/evaluate" \
  -H 'content-type: application/json' \
  -d '{"application_id":"demo-refer","exposure_amount":"350000.00","model_version_id":"credit-model-v4","desk_id":"desk-default"}'
echo ""
echo "credit-demo-gold OK"
