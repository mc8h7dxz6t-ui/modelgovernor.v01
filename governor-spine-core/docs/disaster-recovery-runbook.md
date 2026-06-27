# Governor Spine — Disaster Recovery Runbook

**Classification:** Operational runbook — deployment & business continuity  
**Maturity:** Institutional Self-Check Certified (not third-party audit)

## Mode topology (honest)

Degradation is **already implemented** in each governor's sidecar — not via a new global singleton:

| Symptom | Existing mechanism | Location |
|---------|------------------|----------|
| Redis unavailable | Local guardrail fallback | `guardrails.py`, `fallback_limiter.py` |
| Redis flapping | Circuit breaker opens | `circuit_breaker.py` |
| Operator halt | Diagnostic mode (writes off) | `diagnostic_mode.py` |
| LLM provider down | `PROVIDER_MODE=mock` | ModelGovernor gateway |
| Platform without spine | `*_SPINE_ENABLED=false` | Platform SDK / SpineAdapter |

See `governor-spine-core/spine_core/mode_contract.py` for env var mapping.

## Active → degraded (automatic)

1. Redis guardrail errors increment circuit breaker failures.
2. After threshold, circuit opens; local in-process fallback serves rate/depth limits.
3. Diagnostic mode can be set via admin API — crystallize/commit return 503.

**Do not** patch Kubernetes deployments to mock mode based on `curl openai.com` — that is not a production failover pattern.

## Recovery to active

1. Restore Redis / Postgres connectivity.
2. Clear diagnostic mode: `POST /internal/diagnostic/clear` (admin token).
3. Circuit breaker recovers on successful Redis ping (`record_success`).
4. For ModelGovernor live providers: set `PROVIDER_MODE=live` and supply API keys.

## Verification

```bash
make plug                                    # offline institutional self-check
python -m spine_core.port_checks             # port alignment only
# Live stack (optional):
make cg-stack-up
curl -sf -H 'x-internal-token: dev-cg-spine-token-change-me' \
  http://localhost:8121/internal/security/verify-chain
```

## Chain integrity

Cryptographic verification is **per-governor** via sidecar HTTP APIs — hash algorithms match each domain's seal module. Use `verify_http.verify_domain_chain_http()` or the governor's native `verify-chain` endpoint; do not re-hash in a parallel DB client with invented schemas.
