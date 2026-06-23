# Enterprise hardening roadmap

This document responds to institutional architecture review findings and maps
**implemented fixes** vs **planned enterprise upcharges**.

---

## Part 1 — Critical reliability fixes

### 1. Redis split-brain guardrail bypass ✅ Implemented

**Problem:** When Redis fails, guardrails degraded to unlimited Postgres load.

**Fix:** `sidecar/app/fallback_limiter.py` — thread-safe in-process token bucket
plus per-user rate/in-flight/trace caps when Redis is unavailable.

| Setting | Default | Purpose |
|---|---|---|
| `FALLBACK_GLOBAL_TOKENS_PER_SECOND` | 20 | Global token bucket refill |
| `FALLBACK_TOKEN_BUCKET_CAPACITY` | 40 | Burst cap |
| `FALLBACK_RATE_LIMIT_PER_MINUTE` | 60 | Per-user minute window |
| `FALLBACK_MAX_USER_INFLIGHT` | 5 | In-flight cap during outage |

Metrics: `local_fallback_*_total`, `guardrail_degraded_total`.

### 2. NUMERIC(18,6) micro-token precision ✅ Implemented

**Problem:** $0.00000015/token rounds to zero at 6 decimal places.

**Fix:** Migration `0008_micro_token_precision.sql` upgrades monetary columns to
`NUMERIC(24,12)`. Application quantum: `Decimal("0.000000000001")` via `sidecar/app/money.py`.

### 3. Finance audit poison pill ✅ Implemented

**Problem:** Invariant violation failed reconciler `/readyz`, freezing recovery.

**Fix:** `sidecar/app/diagnostic_mode.py` — cluster-wide diagnostic flag (Redis +
local). On violation:

- Critical alert counter: `finance_audit_diagnostic_entered_total`
- **Sweeps halted** (reconciler stays `/readyz` 200 with `"status":"diagnostic"`)
- **Sidecar writes blocked** (`/reserve` → 503) while `/internal/*` read APIs remain up
- Operators can investigate and `clear_diagnostic_mode()` after repair

Prometheus alert: `ModelGovernorFinanceDiagnosticMode` (see `prometheus-rules.yaml`).

---

## Part 2 — Enterprise upcharges (roadmap)

```
[Current Base] ──► [API Gateway Auth] ──► [Mutual TLS] ──► [Enterprise sign-off]
  Internal token      OIDC / Keycloak       Istio/Envoy         Sealed audit logs
```

### 1. Corporate identity (OIDC / RBAC) — Scaffold shipped ✅

| Today | Target |
|---|---|
| `SIDECAR_INTERNAL_TOKENS` static string | OAuth2/OIDC middleware on `/internal/*` |
| Single token class | RBAC: Viewer vs Financial Admin |

**Shipped:** `sidecar/app/auth_oidc.py` — JWT validation via JWKS (`PyJWT`), Keycloak
`realm_access.roles` and Okta `groups` mapping. Internal token fallback during migration.

| Role | Endpoints |
|---|---|
| Viewer | `GET /internal/*` read surfaces |
| Financial Admin | `POST /internal/diagnostic/clear` and other destructive ops |

Enable with `OIDC_ENABLED=true`, `OIDC_ISSUER_URL`, `OIDC_AUDIENCE`.

**Remaining:** Gateway-level OIDC termination, full audit log of admin actions per subject.

### 2. Tamper-evident ledger sealing — Verification shipped ✅

**Fix (foundation):** Migration `0009_ledger_hash_chain.sql` adds `prev_hash` /
`row_hash` to `ledger_events`. `sidecar/app/ledger_seal.py` SHA-256 chains each event
to the previous row on Postgres.

**Shipped:** `GET /internal/ledger/verify-chain` (422 on break), hourly
`ledger-chain-verify` CronJob, alert `ModelGovernorLedgerChainVerificationFailed`.

**Remaining:** External anchor (S3 Object Lock / transparency log).

### 3. Zero-trust egress — Planned

| Today | Target |
|---|---|
| NetworkPolicy for in-cluster traffic | Egress proxy / service mesh |
| Gateway needs public LLM APIs | Envoy/Istio allowlist: `api.openai.com`, `api.anthropic.com` only |

**Scaffold:** `deploy/base/egress-policy.yaml` (documented) + Istio `ServiceEntry` examples
in `deploy/overlays/enterprise/`.

---

## Operational playbooks

### Redis outage

1. Confirm `guardrail_degraded_total` and `local_fallback_*` metrics
2. Restore Redis HA — guardrails auto-resume distributed mode
3. Postgres pool should remain stable due to fallback token bucket

### Diagnostic mode engaged

1. Page on `ModelGovernorFinanceDiagnosticMode`
2. Use `GET /internal/operations?status=STRANDED` and wallet/trace admin APIs
3. Repair data, run finance audit manually, `POST /internal/diagnostic/clear` (Financial Admin)
4. Confirm sweeps resume and `/reserve` accepts traffic

### Precision migration

Apply `0008` during maintenance window on Postgres. No application downtime required
if sidecar rolls after migration.

---

## Related

- `docs/slo-definitions.md`
- `docs/gitops.md`
- `docs/observability.md`
