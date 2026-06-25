#!/usr/bin/env bash
# Institutional++ reliability & robustness steps (sourced by demo-gold.sh).
set -euo pipefail

step "7/12  Idempotency — safe replay without double-spend"
IDEM_KEY="gold-idem-$(date +%s)"
IDEM_TRACE="trace-idem"
curl -fsS -X POST "http://localhost:8081/reserve" \
  "${HDR[@]}" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"$IDEM_TRACE\",\"idempotency_key\":\"$IDEM_KEY\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"1.000000\"}" >/dev/null
curl -fsS -X POST "http://localhost:8081/settle" \
  "${HDR[@]}" \
  -d "{\"idempotency_key\":\"$IDEM_KEY\",\"outcome\":\"SETTLED\",\"actual_cost\":\"1.000000\",\"provider_request_id\":\"idem-provider-$IDEM_KEY\"}" >/dev/null
REPLAY=$(curl -fsS -X POST "http://localhost:8081/reserve" \
  "${HDR[@]}" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"$IDEM_TRACE\",\"idempotency_key\":\"$IDEM_KEY\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"1.000000\"}")
REPLAY_STATUS=$(echo "$REPLAY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null || echo "?")
echo "  Replay reserve status: $REPLAY_STATUS (expect SETTLED)"
curl -fsS "http://localhost:8081/metrics" -H "x-internal-token: $TOKEN" \
  | grep -E "reserve_idempotent_replay_total" | head -3 || true
echo "  Sales point: append-only ledger + idempotent lifecycle — retries never double-charge"

step "8/12  Provider circuit breaker — storm protection"
clear_provider_circuit "gpt-4o-mini"
open_provider_circuit "gpt-4o-mini"
CB_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8081/reserve" \
  "${HDR[@]}" \
  -d '{"user_id":"demo-user","trace_id":"trace-circuit","idempotency_key":"gold-circuit-block","model":"gpt-4o-mini","estimated_cost":"1.000000"}')
echo "  Reserve with circuit open: HTTP $CB_CODE (expect 409)"
curl -fsS "http://localhost:8081/metrics" -H "x-internal-token: $TOKEN" \
  | grep -E "provider_circuit_open_total" | head -3 || true
clear_provider_circuit "gpt-4o-mini"
echo "  Sales point: per-provider circuit breaker + local fallback when Redis degrades"

step "9/12  Redis guardrail degradation — bounded local fallback"
ensure_redis_up
compose stop redis >/dev/null 2>&1
sleep 2
FB_KEY="gold-fallback-$(date +%s)"
FB_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8081/reserve" \
  "${HDR[@]}" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"trace-redis-fallback\",\"idempotency_key\":\"$FB_KEY\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"1.000000\"}")
echo "  Reserve during Redis outage: HTTP $FB_CODE (expect 200 — local token-bucket fallback)"
curl -fsS -X POST "http://localhost:8081/settle" \
  "${HDR[@]}" \
  -d "{\"idempotency_key\":\"$FB_KEY\",\"outcome\":\"SETTLED\",\"actual_cost\":\"1.000000\",\"provider_request_id\":\"fallback-$FB_KEY\"}" >/dev/null 2>&1 || true
curl -fsS "http://localhost:8081/metrics" -H "x-internal-token: $TOKEN" \
  | grep -E "guardrail_degraded_total|local_fallback_reserve_total" | head -5 || true
ensure_redis_up
echo "  Sales point: symmetric degradation — guardrails + circuit breakers never bypass Postgres truth"

step "10/12  Drift enforcement — over-settle locks wallet deterministically"
DRIFT_KEY="gold-drift-$(date +%s)"
DRIFT_PROVIDER="provider-$DRIFT_KEY"
curl -fsS -X POST "http://localhost:8081/reserve" \
  "${HDR[@]}" \
  -d "{\"user_id\":\"demo-user\",\"trace_id\":\"trace-drift\",\"idempotency_key\":\"$DRIFT_KEY\",\"model\":\"gpt-4o-mini\",\"estimated_cost\":\"${DEMO_DRIFT_RESERVE_COST}\"}" >/dev/null
curl -fsS -X POST "http://localhost:8081/settle" \
  "${HDR[@]}" \
  -d "{\"idempotency_key\":\"$DRIFT_KEY\",\"outcome\":\"SETTLED\",\"actual_cost\":\"${DEMO_DRIFT_ACTUAL_COST}\",\"provider_request_id\":\"$DRIFT_PROVIDER\"}" >/dev/null
LOCK_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8081/reserve" \
  "${HDR[@]}" \
  -d '{"user_id":"demo-user","trace_id":"trace-drift-post-lock","idempotency_key":"demo-post-lock","model":"gpt-4o-mini","estimated_cost":"1.000000"}')
echo "  Post-drift reserve: HTTP $LOCK_CODE (expect 409)"
WALLET_LOCK=$(curl -fsS "http://localhost:8081/internal/wallet/demo-user" -H "x-internal-token: $TOKEN")
echo "$WALLET_LOCK" | python3 -m json.tool 2>/dev/null || echo "$WALLET_LOCK"
curl -fsS "http://localhost:8081/metrics" -H "x-internal-token: $TOKEN" \
  | grep -E "drift_enforced_total" | head -3 || true
echo "  Sales point: micro-cent drift tolerance — breach auto-locks wallet, no silent overspend"

step "11/12  Reconciler leadership + privileged admin audit + ledger trail"
RECON=$(curl -fsS "http://localhost:8082/readyz")
echo "$RECON" | python3 -m json.tool 2>/dev/null || echo "$RECON"
echo ""
echo "  Privileged admin audit (diagnostic clear + operator actions):"
curl -fsS "http://localhost:8081/internal/admin/audit/recent?limit=5" -H "x-internal-token: $TOKEN" \
  | python3 -m json.tool 2>/dev/null | head -35
echo ""
echo "  Recent ledger events:"
curl -fsS "http://localhost:8081/internal/events/recent?limit=8" -H "x-internal-token: $TOKEN" \
  | python3 -m json.tool 2>/dev/null | head -40
echo ""
echo "  Sales point: leader-elected reconciler, hash-chained events, admin audit log — institutional++ proof plane"
