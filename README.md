# modelgovernor.v01

## Institutional-Grade AI Governance Gateway

Reliable, robust, and policy-enforced multi-provider LLM control with auditable ledger-backed accounting and deterministic spend governance.

modelgovernor.v01 is an institutional-grade AI governance gateway for organizations that require strict spend control, enforceable model policy, auditable ledger-backed accounting, and provider-agnostic multi-provider routing.

It combines:
- an OpenAI-compatible gateway layer,
- a hardened policy enforcement sidecar,
- a Postgres-backed escrow and audit ledger,
- Redis-based runtime guardrails,
- and portable local-to-production deployment.

The system is designed to support serious governance standards for AI infrastructure across laptops, VPS deployments, cloud environments, and enterprise platforms.

## Core capabilities

- OpenAI-compatible multi-provider gateway
- Strict model policy registry
- Reserve-before-dispatch spend controls
- Postgres-backed escrow ledger
- Append-only audit trail
- Replay-safe idempotency controls
- Per-trace atomic budget enforcement
- Provider-attempt tracking and late-settlement recovery
- Drift anomaly enforcement with wallet lockout
- Runtime trace and concurrency guardrails
- Deterministic stale-reservation reconciliation
- Portable Docker-first deployment

## Architecture overview

modelgovernor.v01 is built as a layered control plane:

1. **Gateway layer** using LiteLLM for provider normalization and routing.
2. **Policy sidecar** for reserve, settle, refund workflows and policy enforcement.
3. **Postgres ledger** as the system of record for balances, reservations, and audit events.
4. **Redis guardrails** for trace depth, concurrency controls, and short-window rate limits.
5. **Reconciler worker** for stale reservation cleanup, stranded-hold transitions, and append-only operational repair.

## Institutional-grade design principles

- Provider-agnostic routing through a centralized gateway
- Strict model allowlists and policy registry enforcement
- Reserve-before-dispatch cost controls
- Exact-decimal ledger accounting in PostgreSQL
- Append-only audit event history
- Idempotent settlement and replay protection
- Trace-cap enforcement on an authoritative trace state row
- Separate logical-operation identity from provider dispatch attempts
- Runtime guardrails for traces, concurrency, and request velocity
- Deterministic reconciliation for stale reservations
- Portable deployment across local, VPS, and cloud environments

## Operational note

Scaled deployments should use intentionally small application-side SQLAlchemy pools and a database proxy such as PgBouncer or RDS Proxy in front of Postgres. The sidecar and reconciler expose environment-driven pool settings, but the design assumes transaction-level pooling for horizontally scaled fleets.

## Repository layout

```text
README.md
.env.example
docker-compose.yml

docs/
  architecture.md
  build-plan.md
  quality-bar.md

gateway/
  litellm.config.yaml
  README.md

migrations/
  0001_init.sql
  0002_seed_model_policy.sql

sidecar/
  Dockerfile
  requirements.txt
  app/
    main.py
    config.py
    schemas.py
    auth.py
    db.py
    policy.py
    metrics.py
    routes_reserve.py
    routes_settle.py

reconciler/
  Dockerfile
  requirements.txt
  app/
    main.py
    db.py
    sweeper.py

tests/
  integration/
    test_ledger_hardening.py    # fast SQLite-backed correctness tests
    test_postgres_vigorous.py   # institutional-grade Postgres proof tests
  load/
    test_load_harness.py        # reproducible benchmark/load harness

docs/
  architecture.md
  reliability-testing.md        # test-tier guide and CI integration
```

## Testing

modelgovernor.v01 has two clearly separated testing tiers.  See
[`docs/reliability-testing.md`](docs/reliability-testing.md) for the full guide.

### Tier 1 — Fast correctness tests (SQLite, no infra needed)

```bash
pytest tests/integration/test_ledger_hardening.py -v
```

Runs in under one second.  Covers all state-machine transitions, trace-cap
enforcement, reconciler sweep, late settlement, drift lockout, and concurrent
reserve safety.

### Tier 2 — Institutional-grade Postgres proof tests

```bash
# Start ephemeral Postgres
docker-compose -f docker-compose.test.yml up -d postgres-test

# Run against real Postgres semantics
POSTGRES_TEST_URL=******localhost:5433/mg_test \
    pytest tests/integration/test_postgres_vigorous.py -v
```

Validates: atomic UPDATE-RETURNING for trace-cap, `FOR UPDATE SKIP LOCKED`
preventing duplicate reconciler refunds, ENUM type enforcement, JSONB metadata,
`provider_request_id` uniqueness, concurrent reconciler race safety, and
post-session invariant consistency.

### Load / benchmark harness

```bash
# SQLite (fast):
python tests/load/test_load_harness.py

# Postgres (institutional proof):
POSTGRES_TEST_URL=******localhost:5433/mg_test python tests/load/test_load_harness.py
```

Exercises hot-trace contention, distributed contention, and mixed
reserve/settle/sweep activity.  Captures p50/p95/p99 latency and writes a
machine-readable JSON report artifact to `tests/load/reports/`.

## Development roadmap

### Phase 1
- Monorepo scaffold
- Docker Compose local stack
- Postgres schema and seed policies
- Sidecar reserve and settle APIs
- Reconciler daemon
- LiteLLM gateway configuration

### Phase 2
- Metrics and alerts
- Per-trace spend caps
- Provider request ID capture
- Hardened degraded-mode policies
- Admin workflows and operational tooling

### Phase 3
- Provider reconciliation workflows
- Enterprise deployment automation
- Advanced reporting and anomaly detection
- Multi-region operational strategies

## Quality standard

All changes should meet the repository quality bar in `docs/quality-bar.md`.

## Status

Repository scaffold in progress on branch `copilot/scaffold-institutional-v1`.
