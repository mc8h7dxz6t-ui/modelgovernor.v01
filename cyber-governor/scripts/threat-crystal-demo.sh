#!/usr/bin/env bash
set -euo pipefail

SIDECAR="${CG_SIDECAR_URL:-http://localhost:8101}"
GATEWAY="${CG_GATEWAY_URL:-http://localhost:8100}"
TOKEN="${CG_INTERNAL_TOKEN:-dev-cg-spine-token-change-me}"

echo "==> Threat Crystal Protocol demo (multi-vector Shadow Gap)"

echo "1) Arm trusted session (IdentityGate)"
curl -sf -X POST http://localhost:8103/session/arm \
  -H 'content-type: application/json' \
  -d '{"session_id":"tcp-demo-1","user_id":"alice@corp.example","device_fingerprint":"dev_fp_trusted_workstation","client_ip":"10.0.1.42"}'

echo ""
echo "2) Block hijacked session"
curl -sf -X POST http://localhost:8103/session/arm \
  -H 'content-type: application/json' \
  -d '{"session_id":"tcp-demo-2","user_id":"alice@corp.example","device_fingerprint":"attacker_device","client_ip":"203.0.113.9"}'

echo ""
echo "3) Witness log erasure attempt (CloudTrail)"
curl -sf -X POST http://localhost:8105/ingest/cloudtrail \
  -H 'content-type: application/json' \
  -d '{"detail":{"eventName":"DeleteTrail","eventID":"tcp-demo-evt","userIdentity":{"arn":"arn:aws:iam::123:user/attacker"}}}'

echo ""
echo "4) Governed commit via gateway"
curl -sf -X POST "$GATEWAY/governed/commit" \
  -H 'content-type: application/json' \
  -d '{"platform":"egress_lock","operation_id":"tcp-demo-egress","facets":{"destination":"s3://corp-backup","byte_count":2048,"principal_id":"alice@corp.example"},"policy_id":"egress-critical-us"}'

echo ""
echo "5) Forensic reconstruct — recent security events"
curl -sf -H "x-internal-token: $TOKEN" "$SIDECAR/internal/events/recent?limit=8"

echo ""
echo "threat-crystal-demo OK"
