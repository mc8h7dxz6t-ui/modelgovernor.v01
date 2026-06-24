#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/demo-gold-lib.sh"

load_env
wait_for_sidecar
wait_for_gateway
wait_for_reconciler
reset_demo_gold_state

TOKEN="${SIDECAR_PRIMARY_TOKEN}"
TRACE_GOLD="trace-gold-$(date +%s)"
HDR=(-H "x-internal-token: $TOKEN" -H "content-type: application/json")
GW_HDR=(-H "x-internal-token: $TOKEN" -H "content-type: application/json")

banner "ModelGovernor Institutional++ — LIVE SALES DEMO"
echo "Audience: enterprise buyers | Mode: mock providers (zero external deps)"
echo "Duration: ~3 minutes | Command: make demo-gold"
echo ""

step "1/7  Platform health — all control-plane surfaces ready"
curl -fsS "http://localhost:8081/readyz" | head -c 200 && echo " … sidecar ✓"
curl -fsS "http://localhost:8080/readyz" | head -c 200 && echo " … gateway ✓"
curl -fsS "http://localhost:8082/readyz" | head -c 200 && echo " … reconciler ✓"
echo ""
echo "  Sales point: HA topology — gateway + policy sidecar + reconciler leader election"

step "2/7  Governed dispatch — reserve → provider → settle (gateway OIDC-ready)"
OP_KEY="gold-demo-$(date +%s)"
DISPATCH=$(curl -fsS -X POST "http://localhost:8080/governed/dispatch" \
  "${GW_HDR[@]}" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"$TRACE_GOLD\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"5.000000\",\"idempotency_key\":\"$OP_KEY\",\"prompt\":\"Explain reserve-before-dispatch in one sentence.\"}")
echo "$DISPATCH" | python3 -m json.tool 2>/dev/null || echo "$DISPATCH"
echo ""
OPENAI_RESP=$(curl -fsS -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "content-type: application/json" \
  -d "{\"model\":\"gpt-4o-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"One sentence on governed LLM spend.\"}],\"user\":\"demo-user\"}")
echo "  OpenAI SDK drop-in (/v1/chat/completions):"
echo "$OPENAI_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  ', d['choices'][0]['message']['content'][:120])" 2>/dev/null || echo "$OPENAI_RESP"
echo ""
echo "  Sales point: OpenAI / Anthropic / Vertex routers plug in with PROVIDER_MODE=live"

step "3/7  Multi-provider routing (mock — same gateway, different models)"
for MODEL in "anthropic/claude-3-5-haiku-latest" "vertex/gemini-1.5-flash"; do
  SUB_KEY="gold-${MODEL//[\/]/-}-$(date +%s)"
  RESULT=$(curl -fsS -X POST "http://localhost:8080/governed/dispatch" \
    "${GW_HDR[@]}" \
    -d "{\"user_id\":\"demo-user\",\"trace_id\":\"trace-multi\",\"model\":\"$MODEL\",\"estimated_cost\":\"3.000000\",\"idempotency_key\":\"$SUB_KEY\",\"prompt\":\"ping\"}")
  PROVIDER=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('provider_name','?'))" 2>/dev/null || echo "mock")
  COST=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('actual_cost','?'))" 2>/dev/null || echo "?")
  echo "  ✓ $MODEL → provider=$PROVIDER cost=$COST"
done
echo ""
echo "  Sales point: one governance gateway, every LLM supplier — unified ledger"

step "4/7  Tamper-evident ledger — hash-chain verification"
VERIFY=$(curl -fsS "http://localhost:8081/internal/ledger/verify-chain" -H "x-internal-token: $TOKEN" || true)
if echo "$VERIFY" | grep -q '"valid"'; then
  echo "$VERIFY" | python3 -m json.tool 2>/dev/null || echo "$VERIFY"
  echo "  Sales point: SHA-256 hash chain + hourly CronJob + S3 Object Lock anchor (production)"
else
  echo "  (chain verification: events sealing — run a few more dispatches to populate)"
  curl -fsS "http://localhost:8081/internal/events/recent?limit=5" -H "x-internal-token: $TOKEN" | python3 -m json.tool 2>/dev/null | head -20
fi

step "5/7  Diagnostic mode — finance incident without bricking ops"
redis-cli -h localhost HSET mg:diagnostic_mode active 1 component sales-demo reason "synthetic audit drill" >/dev/null 2>&1 || \
  redis_cli HSET mg:diagnostic_mode active 1 component sales-demo reason "synthetic audit drill" >/dev/null
DENY_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8081/reserve" \
  "${HDR[@]}" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"t-diag\",\"idempotency_key\":\"diag-block\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"1.000000\"}")
echo "  Reserve during diagnostic mode: HTTP $DENY_CODE (expect 503)"
DIAG=$(curl -fsS "http://localhost:8081/internal/diagnostic/status" -H "x-internal-token: $TOKEN")
echo "$DIAG" | python3 -m json.tool 2>/dev/null || echo "$DIAG"
curl -fsS -X POST "http://localhost:8081/internal/diagnostic/clear" -H "x-internal-token: $TOKEN" >/dev/null
echo "  Operator recovery: POST /internal/diagnostic/clear → writes admin audit log"
echo "  Sales point: poison-pill fix — sweeps halt, admin APIs stay up, cluster recovers"

step "6/7  Observability — SLO metrics + invariant counters"
echo "  Prometheus scrape (unauthenticated):"
curl -fsS "http://localhost:8081/metrics/prometheus" | grep -E "modelgovernor_http|invariant" | head -8 || true
echo ""
echo "  Operator deep metrics (sample):"
curl -fsS "http://localhost:8081/metrics" -H "x-internal-token: $TOKEN" | grep -E "ledger_events|operations_total|invariant" | head -8 || true
echo ""
echo "  Sales point: 99.5% reserve SLO, burn-rate alerts, governance canary CronJobs"

step "7/7  Wallet + audit trail (Postgres authoritative)"
curl -fsS "http://localhost:8081/internal/wallet/demo-user" -H "x-internal-token: $TOKEN" | python3 -m json.tool 2>/dev/null
echo ""
curl -fsS "http://localhost:8081/internal/events/recent?limit=5" -H "x-internal-token: $TOKEN" | python3 -m json.tool 2>/dev/null | head -30

banner "DEMO COMPLETE — plug-and-play production modules"
cat <<'EOF'
  ┌────────────────────────────┬──────────────────────────────────────────┐
  │ Demo (running now)         │ Production (flip env / overlay)          │
  ├────────────────────────────┼──────────────────────────────────────────┤
  │ PROVIDER_MODE=mock         │ live + OpenAI/Anthropic/Vertex keys      │
  │ Internal token auth        │ OIDC / Keycloak / Okta at gateway+sidecar│
  │ Single Redis container     │ Redis Sentinel or ElastiCache            │
  │ Local Postgres             │ PgBouncer + ExternalSecrets + GitOps     │
  │ —                          │ Istio mTLS + egress allowlist            │
  │ —                          │ S3 Object Lock ledger anchor             │
  └────────────────────────────┴──────────────────────────────────────────┘

  Docs:  docs/sales-demo.md  |  docs/capability-matrix.md  |  docs/plug-and-play.md
  GitOps: deploy/overlays/production  |  deploy/helm/modelgovernor
  Tests:  57+ Tier-1 integration tests  |  chaos + load tiers in CI

EOF
echo "Teardown: make demo-gold-down"
echo ""
