# Operations Runbook

## Purpose

This runbook captures the minimum operating expectations for deploying
`modelgovernor.v01` as a credible production control plane.  It is intentionally
focused on startup assumptions, rollout order, observability, and recovery
paths rather than feature design.

---

## Core services and startup expectations

### Required services

- **Postgres 14+** as the authoritative ledger and audit system of record
- **Redis 6+** for volatile runtime guardrails only
- **Sidecar** FastAPI service exposing governance APIs, `/healthz`, `/readyz`,
  `/metrics`, and `/metrics.json`
- **Reconciler** scheduled worker for deterministic expiry and stranded-hold
  repair
- **Gateway** calling the sidecar with a valid internal token

### Required secrets and environment

At minimum, production deployments must provide:

- `DATABASE_URL`
- `REDIS_URL`
- `SIDECAR_INTERNAL_TOKENS`

Common runtime controls that should be set deliberately rather than left
implicit:

- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `DB_POOL_TIMEOUT_SECONDS`
- `DB_POOL_RECYCLE_SECONDS`
- `DEFAULT_TRACE_CAP_AMOUNT`
- `DRIFT_ABSOLUTE_TOLERANCE`
- `DRIFT_RATIO_TOLERANCE`
- `ORCHESTRATION_RUNTIME_MODE`
- `ORCHESTRATION_SHADOW_MODE`
- `ORCHESTRATION_CACHE_TTL_SECONDS`

Use externally managed secrets.  Do not commit production values into the
repository or Kubernetes manifests.

---

## Health, readiness, and safe startup

### Sidecar probes

- `GET /healthz` returns process liveness
- `GET /readyz` returns request-readiness for the HTTP service
- `GET /metrics` exposes Prometheus text format
- `GET /metrics.json` exposes a JSON snapshot of invariant counters for tests
  and load reports

The Kubernetes deployment already wires `/healthz` as a liveness probe and
`/readyz` as a readiness probe.  Treat failing readiness as a release blocker.

### Startup order

1. Provision Postgres and Redis.
2. Create or refresh the `modelgovernor-secrets` secret (or equivalent external
   secret injection).
3. Apply migrations in lexical order from `migrations/0001_init.sql` through the
   latest file.
4. Start or roll the sidecar deployment.
5. Confirm `/readyz` and `/metrics` respond before sending governed traffic.
6. Start the reconciler Deployment (`RECONCILER_MODE=daemon`) only after the database
   schema is current and Redis is reachable (required for cluster-wide diagnostic mode).

### Rollout guardrails

- Do not route production traffic until sidecar readiness probes pass.
- Keep application-side SQL pools intentionally small and use PgBouncer, RDS
  Proxy, or an equivalent transaction-pooling proxy in front of Postgres.
- Prefer zero-downtime rollouts (`maxSurge=1`, `maxUnavailable=0`) for sidecar
  updates.

---

## Validation checklist before promotion

Run or confirm the following:

- `python -m compileall -q sidecar/app reconciler/app`
- Tier 1 SQLite integration tests
- Tier 2 Postgres vigorous tests
- Tier 3 load harness
- Kubernetes overlay rendering for staging and production
- Migration parse sanity check against SQLite-compatible SQL

Promotion should stop if any of these are flaky, environment-sensitive, or
inconsistent with documented behavior.

---

## Observability expectations

### Minimum signals

Operators should be able to observe:

- reserve success and denial rates
- drift tolerated versus drift enforced
- reconciler claimed, expired, and stranded counts
- negative wallet anomalies
- duplicate settlement or refund anomaly detection
- audit-log activity for privileged admin actions
- orchestration workflow outcomes and cache/critic behavior

### Built-in surfaces

- Prometheus scrape endpoint: `GET /metrics/prometheus` (unauthenticated, PodMonitor)
- Operator metrics with DB aggregates: `GET /metrics` (requires internal token)
- JSON invariant snapshot: `GET /metrics.json`
- Wallet status: `GET /internal/wallet/{user_id}`
- Operation status: `GET /internal/operation/{idempotency_key}`
- Trace budget: `GET /internal/trace/{trace_id}`
- Recent audit events: `GET /internal/events/recent`
- Diagnostic mode status: `GET /internal/diagnostic/status`
- Clear diagnostic mode (Financial Admin): `POST /internal/diagnostic/clear`
- Ledger hash-chain verification: `GET /internal/ledger/verify-chain` (422 on tamper)
- Ledger head anchor: `POST /internal/ledger/anchor-head` (Financial Admin)
- Privileged admin audit: `GET /internal/admin/audit/recent`
- Attribution summary: `GET /internal/attribution/summary`
- Guardrail incidents: `GET /internal/guardrail/incidents`
- Execution lineage: `GET /internal/lineage/{idempotency_key}`

### Alerting baseline

The shipped Prometheus rules alert on:

- reserve availability and latency SLO breaches
- balance-denied reserve spikes
- drift-enforced lockouts
- increasing stranded operations
- negative wallet invariant violations
- post-sweep finance audit failures
- finance diagnostic mode entry
- ledger hash-chain verification failures
- Redis guardrail degradation

Treat missing scrape data, repeated readiness failures, or sustained stranded
growth as operational incidents even when hard alerts have not yet fired.

---

## Recovery playbooks

### Drift lockout

Symptoms:
- `drift_enforced_total` increases
- affected wallet is locked

Response:
1. Confirm the authoritative provider usage and expected final charge.
2. Review audit events for the affected operation and wallet.
3. Correct or settle the operation through the documented admin workflow.
4. Unlock the wallet only after manual review and corrective settlement.

### Stranded operations growing

Symptoms:
- `reconciler_stranded_total` rising
- `GET /internal/events/recent` shows accumulating `STRANDED_HOLD` events

Response:
1. Verify provider outcome for each stranded operation.
2. Apply deterministic correction via late settlement or manual ops procedure when the
   authoritative spend is known.
3. Confirm the correction is captured in the admin audit log.

### Reconciler not sweeping

Symptoms:
- expired holds remain `RESERVED`
- `modelgovernor_reconciler_leader == 0` for 15+ minutes
- reconciler pod logs show sweep errors or diagnostic mode active

Response:
1. Check reconciler Deployment pod logs and `/readyz` on port 8082.
2. Verify `DATABASE_URL`, `REDIS_URL`, and database reachability.
3. Confirm migrations are current and no pod holds the advisory lock indefinitely.
4. If diagnostic mode is active, repair data then `POST /internal/diagnostic/clear`.

### Redis unavailable

Symptoms:
- `guardrail_degraded_total` and `provider_circuit_local_fallback_total` increasing
- `local_fallback_rate_limit_total` under surge

Response:
1. Confirm reserve/settle still operate against Postgres (with per-pod local limits).
2. Restore Redis or fail over Redis HA.
3. Review local fallback pressure; scale sidecar cautiously if Redis remains down.

### Postgres failover

Symptoms:
- sidecar readiness failures
- connection churn or stale primary references

Response:
1. Promote or confirm the new primary.
2. Re-point PgBouncer or the database proxy.
3. Restart sidecar pods if needed to flush stale connections.
4. Confirm `/readyz` and run a small governed request before reopening traffic.

---

## Governance and security expectations

- Privileged admin routes require `X-Internal-Token` and must remain on trusted
  internal networks only.
- Secrets must come from an external manager, not repository state.
- Governance-critical balance mutations belong in the sidecar/Postgres finance
  plane, not in Redis or orchestration helpers.
- Orchestration workflows are non-authoritative and must not directly mutate
  ledger state.

---

## Exit criteria for “ready”

Treat the platform as ready only when:

- documented validation gates pass consistently
- deployment overlays render cleanly for the target environment
- health/readiness probes and Prometheus scraping work in that environment
- operators can execute the recovery playbooks above
- failover, migration rollout, and secret injection have been rehearsed at least
  once in the target platform
