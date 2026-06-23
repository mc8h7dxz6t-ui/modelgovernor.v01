# modelgovernor.v01

## Institutional-Grade AI Governance Gateway

Reliable, robust, and policy-enforced multi-provider LLM control with auditable ledger-backed accounting and deterministic spend governance.

modelgovernor.v01 is an institutional-grade AI governance gateway for organizations that require strict spend control, enforceable model policy, auditable ledger-backed accounting, and provider-agnostic multi-provider routing.

It combines:
- an OpenAI-compatible gateway layer,
- a hardened policy enforcement sidecar,
- a Postgres-backed escrow and audit ledger,
- Redis-based runtime guardrails,
- a deterministic orchestration plane for multi-agent validation workflows,
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
- Dual-plane orchestration (co-existing + standalone runtime modes)
- Portable Docker-first deployment

## Architecture overview

modelgovernor.v01 is built as a layered control plane:

1. **Gateway layer** using LiteLLM for provider normalization and routing.
2. **Policy sidecar** for reserve, settle, refund workflows and policy enforcement.
3. **Postgres ledger** as the system of record for balances, reservations, and audit events.
4. **Redis guardrails** for trace depth, concurrency controls, and short-window rate limits.
5. **Reconciler worker** for stale reservation cleanup, stranded-hold transitions, and append-only operational repair.
6. **Orchestration plane** for ingest/retrieve/compute/report/critic workflows with JSON-only outputs and immutable decision logs.

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
  reliability-testing.md
  ha-strategy.md

gateway/
  litellm.config.yaml
  README.md

migrations/
  0001_init.sql
  0002_seed_model_policy.sql
  0003_harden_ledger_constraints.sql
  0004_ledger_control_plane_hardening.sql
  0005_phase3_reconciliation.sql
  0006_audit_report_indexes.sql
  0007_orchestration_plane.sql

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
    ledger.py
    routes_reserve.py
    routes_settle.py
    routes_reconcile.py       ← Phase 3
    routes_orchestration.py   ← Phase 5

reconciler/
  Dockerfile
  requirements.txt
  app/
    main.py
    db.py
    sweeper.py

deploy/                        ← Phase 3
  base/
    kustomization.yaml
    namespace.yaml
    sidecar-deployment.yaml
    sidecar-service.yaml
    reconciler-cronjob.yaml
  overlays/
    staging/kustomization.yaml
    production/kustomization.yaml

tests/
  integration/
    test_ledger_hardening.py        # Tier 1: fast SQLite correctness tests
    test_phase3_reconciliation.py   # Tier 1: Phase 3 reconciliation tests
    test_postgres_vigorous.py       # Tier 2: institutional Postgres proof tests
  load/
    test_load_harness.py            # Tier 3: reproducible benchmark harness
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

### Phase 1 ✓
- Monorepo scaffold
- Docker Compose local stack
- Postgres schema and seed policies
- Sidecar reserve and settle APIs
- Reconciler daemon
- LiteLLM gateway configuration

### Phase 2 ✓
- Metrics and alerts (`/metrics` endpoint + invariant counter module)
- Per-trace spend caps (atomic `trace_budget_state` enforcement)
- Provider request ID capture with uniqueness enforcement
- Hardened degraded-mode policies
- Admin workflows and operational tooling

### Phase 3 ✓
- Provider reconciliation workflows (STRANDED operation surface + admin correction)
- Admin correction API for manual operation settlement
- Reconciliation summary dashboard endpoint
- Wallet unlock workflow for drift-locked wallets
- Admin audit log (`admin_audit_log` table) for all administrative interventions
- Kubernetes deployment manifests (`deploy/base` + `deploy/overlays/{staging,production}`)
- HA and multi-region architecture documentation

### Phase 4 ✓
- Live anomaly-invariant enforcement counters
- Prometheus-native metrics exposition with alerting rules
- Governance reporting and audit export endpoints (internal-auth protected)
- Adaptive Reservation Sizing specification
- CI load-harness gate and production promotion gates

### Phase 5 ✓
- Dual-plane orchestration API (`/orchestration/workflows/run`)
- Co-existing and standalone orchestration runtime modes
- Deterministic compute sandbox for financial math expressions
- Citation-enforced critic validation loop
- Immutable orchestration decision audit log + semantic cache

## Quality standard

All changes should meet the repository quality bar in `docs/quality-bar.md`.

## Status

All five phases are complete.  The platform is production-ready and deployable
from a single Docker Compose command for local development, or via the
Kubernetes manifests in `deploy/` for container platform deployments.
