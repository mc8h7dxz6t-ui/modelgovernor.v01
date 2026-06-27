#!/usr/bin/env bash
# Cybersecurity Governor pilot attestation — spine + sales SKU platforms
set -euo pipefail

TOKEN="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"
SIDECAR="${CG_SIDECAR_URL:-http://localhost:8121}"
GATEWAY="${CG_GATEWAY_URL:-http://localhost:8120}"

echo "==> Cybersecurity Governor Pilot Attestation"
echo "    sidecar=$SIDECAR gateway=$GATEWAY"

curl -sf "$SIDECAR/readyz" >/dev/null
curl -sf "$GATEWAY/readyz" >/dev/null
echo "OK  spine ready"

curl -sf -X POST "$GATEWAY/governed/commit" \
  -H 'content-type: application/json' \
  -d '{"platform":"egress_govern","operation_id":"pilot-egress-1","facets":{"flow_id":"pilot-egress-1","destination_host":"api.openai.com","egress_decision":"ALLOWED"},"policy_id":"egress-critical-us","reserved_budget":"0","committed_budget":"0","outcome":"allowed"}' \
  >/dev/null
echo "OK  governed egress commit"

VERIFY="$(curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/security/verify-chain")"
echo "$VERIFY" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('valid') is True, d"
echo "OK  security chain verified"

ANCHOR="$(curl -sf -X POST -H "x-internal-token: $TOKEN" "$SIDECAR/internal/security/anchor-head")"
echo "$ANCHOR" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('anchored') or d.get('head_hash'), d"
echo "OK  chain head anchored"

if curl -sf http://localhost:8124/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8124/session/arm \
    -H 'content-type: application/json' \
    -d '{"session_id":"pilot-id-1","user_id":"alice@corp.example","device_fingerprint":"dev_fp_trusted_workstation","client_ip":"10.0.1.42"}' >/dev/null
  echo "OK  IdentityGovern session arm"
fi

if curl -sf http://localhost:8123/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8123/egress/evaluate \
    -H 'content-type: application/json' \
    -d '{"flow_id":"pilot-eg-1","destination_host":"api.openai.com"}' >/dev/null
  echo "OK  EgressGovern evaluate"
fi

if curl -sf http://localhost:8129/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8129/ingest/cloudtrail \
    -H 'content-type: application/json' \
    -d '{"detail":{"eventName":"DeleteTrail","eventID":"evt-pilot-1","userIdentity":{"arn":"arn:aws:iam::123:user/bob"}}}' >/dev/null
  echo "OK  WitnessBridge CloudTrail ingest"
fi

if curl -sf http://localhost:8130/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8130/ingest/falco \
    -H 'content-type: application/json' \
    -d '{"rule":"Terminal shell in container","priority":"Critical","output_fields":{"proc.name":"bash","user.name":"root"}}' >/dev/null
  echo "OK  LineageIngest Falco ingest"
fi

if curl -sf http://localhost:8131/healthz >/dev/null 2>&1; then
  curl -sf -X POST http://localhost:8131/content/evaluate \
    -H 'content-type: application/json' \
    -d '{"content_id":"pilot-cg-1","principal_id":"alice@corp.example","text_body":"hello world"}' >/dev/null
  echo "OK  ContentGuard evaluate"
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 cybersecurity-governor/scripts/attestation_runner.py
make cg-certification
python3 cybersecurity-governor/scripts/generate_design_partner_attestation.py
echo "==> Pilot attestation complete"
