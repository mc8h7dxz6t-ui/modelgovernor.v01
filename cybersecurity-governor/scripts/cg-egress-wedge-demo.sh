#!/usr/bin/env bash
# Defensible wedge demo: identity violation → mesh blocks egress commit → ext_authz denies exfil host
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOKEN="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"
SIDECAR="${CG_SIDECAR_URL:-http://localhost:8121}"

ensure_stack() {
  if ! curl -sf "${SIDECAR}/healthz" >/dev/null 2>&1; then
    echo "==> Starting CG stack"
    make -C "$ROOT/cybersecurity-governor" cg-stack-up
    sleep 8
  fi
}

ensure_stack

echo "==> 1. Envoy ext_authz — allowlisted host"
curl -sf -X POST http://localhost:8123/envoy/authz/check \
  -H 'content-type: application/json' \
  -d '{"attributes":{"request":{"http":{"id":"wedge-1","host":"api.openai.com","path":"/v1/chat"}}}}'
echo ""

echo "==> 2. Envoy ext_authz — DENIED off-allowlist"
curl -sf -X POST http://localhost:8123/envoy/authz/check \
  -H 'content-type: application/json' \
  -d '{"attributes":{"request":{"http":{"id":"wedge-2","host":"evil-exfil.example","path":"/upload"}}}}' \
  || echo '{"decision":"DENIED"}'
echo ""

echo "==> 3. IdentityGovern session arm"
curl -sf -X POST http://localhost:8124/session/arm \
  -H 'content-type: application/json' \
  -d '{"session_id":"wedge-1","user_id":"alice@corp.example","device_fingerprint":"dev_fp_trusted","client_ip":"10.0.1.42"}'
echo ""

echo "==> 4. Threat mesh — crystallize identity VIOLATION parent"
curl -sf -X POST "${SIDECAR}/crystallize" \
  -H "x-internal-token: ${TOKEN}" \
  -H 'content-type: application/json' \
  -d '{
    "platform": "identity_govern",
    "operation_id": "wedge-demo-id-viol-1",
    "account_id": "tenant-default",
    "risk_tier": "critical",
    "facets": {
      "principal": "cluster.local/ns/other/sa/evil",
      "workload_sa": "ig-platform-workload",
      "identity_decision": "VIOLATION"
    },
    "policy_id": "identity-high-us",
    "reserved_budget": "0"
  }'
echo ""

EGRESS_FACETS='{"flow_id":"wedge-demo-flow-1","destination_host":"api.anthropic.com","egress_decision":"ALLOWED"}'
CRYSTAL_ID="$(curl -sf -X POST "${SIDECAR}/crystallize" \
  -H "x-internal-token: ${TOKEN}" \
  -H 'content-type: application/json' \
  -d "{
    \"platform\": \"egress_govern\",
    \"operation_id\": \"wedge-demo-flow-1\",
    \"account_id\": \"tenant-default\",
    \"risk_tier\": \"critical\",
    \"facets\": ${EGRESS_FACETS},
    \"policy_id\": \"egress-critical-us\",
    \"reserved_budget\": \"0\"
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['crystal_id'])")"

echo "==> 5. Threat mesh — egress commit must return HTTP 409 (mesh block)"
COMMIT_CODE="$(curl -s -o /tmp/cg-mesh-commit.json -w "%{http_code}" -X POST "${SIDECAR}/commit" \
  -H "x-internal-token: ${TOKEN}" \
  -H 'content-type: application/json' \
  -d "{
    \"crystal_id\": \"${CRYSTAL_ID}\",
    \"facets\": ${EGRESS_FACETS},
    \"committed_budget\": \"0\",
    \"outcome\": \"allowed\"
  }")"

if [[ "${COMMIT_CODE}" != "409" ]]; then
  echo "FAIL: expected HTTP 409 mesh block, got ${COMMIT_CODE}: $(cat /tmp/cg-mesh-commit.json)"
  exit 1
fi
python3 -c "import json; d=json.load(open('/tmp/cg-mesh-commit.json')); assert 'mesh block' in str(d.get('detail','')).lower(), d"
echo "OK    mesh block 409 — $(cat /tmp/cg-mesh-commit.json)"
echo ""

echo "==> 6. Spine chain verify"
curl -sf -H "x-internal-token: ${TOKEN}" "${SIDECAR}/internal/security/verify-chain"
echo ""
echo "cg-egress-wedge-demo OK — ext_authz + mesh 409 + verify-chain"
