#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/cg-demo-lib.sh"

ensure_cg_stack_up

SIDECAR="${CG_SIDECAR_URL:-http://localhost:8101}"
GATEWAY="${CG_GATEWAY_URL:-http://localhost:8100}"
TOKEN="${CG_INTERNAL_TOKEN:-dev-cg-spine-token-change-me}"

echo "==> Cybersecurity Governor — institutional++ security demo"
echo ""

echo "1) Trusted session arm"
curl -sf -X POST http://localhost:8103/session/arm \
  -H 'content-type: application/json' \
  -d '{"session_id":"tcp-demo-1","user_id":"alice@corp.example","device_fingerprint":"dev_fp_trusted_workstation","client_ip":"10.0.1.42"}'
echo ""

echo "2) Session hijack → STRANDED"
curl -sf -X POST http://localhost:8103/session/arm \
  -H 'content-type: application/json' \
  -d '{"session_id":"tcp-demo-2","user_id":"alice@corp.example","device_fingerprint":"attacker_device","client_ip":"203.0.113.9"}'
echo ""

echo "3) CloudTrail DeleteTrail witnessed"
curl -sf -X POST http://localhost:8105/ingest/cloudtrail \
  -H 'content-type: application/json' \
  -d '{"detail":{"eventName":"DeleteTrail","eventID":"tcp-demo-evt","userIdentity":{"arn":"arn:aws:iam::123:user/attacker"}}}'
echo ""

echo "4) Egress blocked (evil destination)"
curl -sf -X POST http://localhost:8104/egress/evaluate \
  -H 'content-type: application/json' \
  -d '{"egress_id":"tcp-demo-egress","principal_id":"alice@corp.example","destination":"evil-exfil.example","byte_count":99999999}'
echo ""

echo "5) Falco lineage → structural DAG"
curl -sf -X POST http://localhost:8106/ingest/falco \
  -H 'content-type: application/json' \
  -d '{"rule":"Terminal shell in container","priority":"Critical","output_fields":{"proc.name":"bash","proc.pname":"sh","user.name":"root"}}'
echo ""

echo "6) Security hash chain verify"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/security/verify-chain"
echo ""

echo "7) Anchor head (witness quorum)"
curl -sf -H "x-internal-token: $TOKEN" -X POST "$SIDECAR/internal/security/anchor-head"
echo ""

echo "8) Recent security events"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/events/recent?limit=8"
echo ""

echo "9) Posture drift → STRANDED"
curl -sf -X POST http://localhost:8107/posture/evaluate \
  -H 'content-type: application/json' \
  -d '{"evaluation_id":"tcp-demo-posture","resource_id":"eks-dr","posture_score":65,"failed_controls":["public_s3_bucket"]}'
echo ""

echo "10) ContentGuard secret leak → BLOCKED"
curl -sf -X POST http://localhost:8108/content/evaluate \
  -H 'content-type: application/json' \
  -d '{"content_id":"tcp-demo-content","principal_id":"alice@corp.example","text_body":"leaked sk-abcdefghijklmnopqrstuvwxyz123456","classification_hint":"restricted"}'
echo ""
echo "cg-security-demo OK"
