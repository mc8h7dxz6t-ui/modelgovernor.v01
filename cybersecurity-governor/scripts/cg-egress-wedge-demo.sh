#!/usr/bin/env bash
# Defensible wedge demo: identity violation → mesh blocks egress commit → ext_authz denies exfil host
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOKEN="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"

ensure_stack() {
  if ! curl -sf http://localhost:8121/healthz >/dev/null 2>&1; then
    echo "==> Starting CG stack"
    make -C "$ROOT/cybersecurity-governor" cg-stack-up
    sleep 5
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

echo "==> 4. Spine chain verify"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8121/internal/security/verify-chain
echo ""
echo "cg-egress-wedge-demo OK — wire Envoy ext_authz filter to http://egress-govern:8123/envoy/authz/check"
