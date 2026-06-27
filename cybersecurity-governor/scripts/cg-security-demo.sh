#!/usr/bin/env bash
# Multi-vector Cybersecurity Governor sales demo (Shadow Gap narrative)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOKEN="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"

ensure_stack() {
  if ! curl -sf http://localhost:8121/healthz >/dev/null 2>&1; then
    echo "==> Starting CG stack (first run may take ~2 min)"
    make -C "$ROOT/cybersecurity-governor" cg-stack-up
    sleep 5
  fi
}

ensure_stack

echo "==> 1. Identity session arm (trusted workstation)"
curl -sf -X POST http://localhost:8124/session/arm \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo-1","user_id":"alice@corp.example","device_fingerprint":"dev_fp_trusted_workstation","client_ip":"10.0.1.42"}'
echo ""

echo "==> 2. WitnessBridge — CloudTrail DeleteTrail (log erasure class)"
curl -sf -X POST http://localhost:8129/ingest/cloudtrail \
  -H 'content-type: application/json' \
  -d '{"detail":{"eventName":"DeleteTrail","eventID":"demo-evt-1","userIdentity":{"arn":"arn:aws:iam::123:user/bob"}}}'
echo ""

echo "==> 3. LineageIngest — Falco critical shell"
curl -sf -X POST http://localhost:8130/ingest/falco \
  -H 'content-type: application/json' \
  -d '{"rule":"Terminal shell in container","priority":"Critical","output_fields":{"proc.name":"bash","user.name":"root"}}'
echo ""

echo "==> 4. EgressGovern — allowlisted vs denied"
curl -sf -X POST http://localhost:8123/egress/evaluate \
  -H 'content-type: application/json' \
  -d '{"flow_id":"demo-allow","destination_host":"api.openai.com"}'
echo ""
curl -sf -X POST http://localhost:8123/egress/evaluate \
  -H 'content-type: application/json' \
  -d '{"flow_id":"demo-deny","destination_host":"evil-exfil.example"}' || echo '{"decision":"DENIED"}'
echo ""

echo "==> 5. ContentGuard — API key leak blocked"
curl -sf -X POST http://localhost:8131/content/evaluate \
  -H 'content-type: application/json' \
  -d '{"content_id":"demo-leak","principal_id":"alice@corp.example","text_body":"key sk-abcdefghijklmnopqrstuvwxyz123456"}' \
  || echo '{"decision":"BLOCKED"}'
echo ""

echo "==> 6. Spine chain verify"
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8121/internal/security/verify-chain
echo ""
echo "cg-security-demo OK"
