# Reliability Testing Guide

This document explains the three testing tiers for `modelgovernor.v01` and the
supporting validation gates around them.  The distinction matters because the
tiered tests and non-functional checks serve different purposes and make
different guarantees.

---

## Tier 1 — Lightweight / Local fast tests

**File:** `tests/integration/test_ledger_hardening.py`

**Engine:** SQLite (in-memory, via `tmp_path`)

**Runs in:** < 1 second, zero external dependencies, always works on a laptop

**Purpose:**
These tests validate the correctness of the ledger logic — state machine
transitions, trace-cap arithmetic, replay idempotency, drift detection, and
reconciler sweep behaviour — in isolation from any infrastructure.

SQLite closely approximates Postgres for the logic under test.  The code is
written to adapt SQL to the dialect in use (`FOR UPDATE SKIP LOCKED` is omitted
for SQLite; JSONB is written as TEXT).

**What these tests prove:**

| Scenario | Covered |
|---|---|
| Reserve → dispatch → settle happy path | ✓ |
| Idempotent replay returns same result | ✓ |
| Mismatched fingerprint raises ConflictError | ✓ |
| Provider failover (multiple dispatch attempts) | ✓ |
| Reconciler strands IN_FLIGHT holds | ✓ |
| Reconciler refunds clean expired holds | ✓ |
| Late settlement after EXPIRED applies correction debit | ✓ |
| Late settlement after STRANDED applies correction debit | ✓ |
| Drift within tolerance: DRIFT_TOLERATED event | ✓ |
| Drift above threshold: wallet locked, DRIFT_ENFORCED event | ✓ |
| Concurrent reserves cannot oversubscribe trace cap | ✓ (SQLite WAL mode) |

**How to run:**

```bash
pytest tests/integration/test_ledger_hardening.py -v
```

---

## Tier 2 — Institutional-grade Postgres-backed vigorous proof tests

**File:** `tests/integration/test_postgres_vigorous.py`

**Engine:** Real Postgres 16

**Requires:** `POSTGRES_TEST_URL` environment variable pointing to a live
Postgres database with no prior migrations applied (or a freshly truncated one).

**Purpose:**
These tests run the same scenarios as Tier 1 but against real Postgres
semantics.  They additionally validate:

- `FOR UPDATE SKIP LOCKED` prevents duplicate refunds in concurrent reconciler
  workers — a property that **cannot** be demonstrated with SQLite.
- Postgres ENUM type transitions (`RESERVED → IN_FLIGHT → SETTLED` etc.)
- JSONB metadata is correctly stored and queriable.
- `provider_request_id` uniqueness index rejects cross-operation ID collisions.
- Concurrent `UPDATE … RETURNING` is atomic under MVCC — no trace cap overrun
  even under maximum thread contention.

**What these tests prove additionally:**

| Scenario | Postgres-specific guarantee |
|---|---|
| Concurrent trace-cap contention (10 workers) | Atomic UPDATE-RETURNING on MVCC |
| provider_request_id uniqueness conflict | Unique partial index on Postgres |
| Concurrent reconciler workers (SKIP LOCKED) | Exactly-once sweep, no duplicate refunds |
| Concurrent reconciler workers — STRANDED rows | Exactly-once stranded event per row |
| ENUM type enforcement | Postgres-native check |
| JSONB metadata queriable | `metadata->>'key'` syntax |
| No negative wallet balances across session | Postgres CHECK constraint + logic |
| No trace reserved_total > cap | Application invariant, session-wide |

**Quickstart (Docker Compose):**

```bash
# Start a clean ephemeral Postgres for the test run
docker-compose -f docker-compose.test.yml up -d postgres-test

# Wait for healthy (or rely on the healthcheck)
docker-compose -f docker-compose.test.yml ps

# Run vigorous tests
POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5433/mg_test \
    pytest tests/integration/test_postgres_vigorous.py -v

# Tear down
docker-compose -f docker-compose.test.yml down
```

**Or run everything in one container:**

```bash
docker-compose -f docker-compose.test.yml run --rm test
```

**If you already have a Postgres instance:**

```bash
export POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@host:5432/mg_test
pytest tests/integration/test_postgres_vigorous.py -v
```

> **Note:** Migrations are applied automatically at the start of the test
> session.  Use a dedicated test database; do not point this at a production
> database.

---

## Tier 3 — Load / benchmark harness

**File:** `tests/load/test_load_harness.py`

**Engine:** SQLite by default; Postgres when `POSTGRES_TEST_URL` is set.

**Purpose:**
Characterises reserve-path latency, invariant safety under load, and
concurrency behaviour.  Produces a machine-readable JSON report artifact.

**Scenarios:**

| Scenario | Description |
|---|---|
| `hot_trace_contention` | All workers share one trace; cap allows ~half to succeed.  Proves zero cap overruns. |
| `distributed_contention` | Each worker gets its own trace.  Measures base reserve latency with no lock pressure. |
| `mixed_activity` | Concurrent reserve / settle / sweep.  Proves no negative balances. |

**Metrics captured:**

- `p50 / p95 / p99` reserve DB transaction duration (ms)
- `invariant_violations` count (must be zero for a passing run)
- Outcome breakdown: `reserved`, `cap_exceeded`, `error:<reason>`
- Counters from `sidecar.app.metrics`: reserve success, denials, drift events,
  reconciler claimed/expired/stranded

**How to run:**

```bash
# Fast, SQLite, always works:
python tests/load/test_load_harness.py

# Or via pytest:
pytest tests/load/test_load_harness.py -v

# With Postgres (institutional proof):
POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5433/mg_test python tests/load/test_load_harness.py

# Tune concurrency:
LOAD_WORKERS=50 LOAD_OPS_PER_WORKER=50 python tests/load/test_load_harness.py
```

**Report output:**

Each run writes a JSON artifact to `tests/load/reports/load_report_<db>_<ts>.json`:

```json
{
  "generated_at": "20260622T185416Z",
  "db_mode": "sqlite",
  "workers": 20,
  "ops_per_worker": 25,
  "scenarios": [
    {
      "scenario": "hot_trace_contention",
      "n": 20,
      "outcomes": {"reserved": 5, "cap_exceeded": 15},
      "latency_ms": {"p50": 2.1, "p95": 8.4, "p99": 12.3},
      "invariant_violations": 0,
      "metrics": { ... }
    }
  ]
}
```

---

## Invariant metrics module

**File:** `sidecar/app/metrics.py`

Provides a process-global thread-safe counter registry.  The following counters
are incremented by the production code paths:

| Counter | Incremented by |
|---|---|
| `reserve_success_total` | Successful reserve commit |
| `reserve_denied_trace_cap_total` | TraceCapExceededError |
| `reserve_denied_balance_total` | InsufficientFundsError |
| `reserve_idempotent_replay_total` | Replay of existing idempotency key |
| `trace_cap_overrun_detected_total` | Same as cap denial |
| `drift_enforced_total` | Drift above threshold → wallet locked |
| `drift_tolerated_total` | Drift within tolerance |
| `reconciler_claimed_total` | Total rows swept per run |
| `reconciler_expired_total` | Rows transitioned to EXPIRED |
| `reconciler_stranded_total` | Rows transitioned to STRANDED |

Phase 4 anomaly enforcement counters (live and tested):

| Counter | Incremented by |
|---|---|
| `negative_wallet_detected_total` | Negative-balance invariant probe |
| `duplicate_refund_anomaly_total` | Duplicate refund attempt detection |
| `duplicate_settlement_anomaly_total` | Duplicate settlement attempt detection |

---

## CI integration

`.github/workflows/ci.yml` runs on every push:

- **Tier 1** (`test-tier1`): ledger hardening, admin observability, Phase 4 anomaly probes, readiness, chaos resilience, property-based ledger tests, migration invariant definitions.
- **Tier 2** (`test-tier2`): Postgres vigorous proof tests plus DB constraint validation against `postgres:16`.
- **Tier 3** (`test-load`): load harness pytest gate plus `python tests/load/test_load_harness.py` with zero-invariant-violation validation; uploads JSON artifact.
- **Migration invariant definitions** (`validate-migrations`): verifies `0005_invariant_constraints.sql` is present.

---

## Production-readiness evidence outside tests

- `/healthz` — process liveness
- `/readyz` — database connectivity probe (503 when DB unreachable)
- `/metrics` — DB-aggregate Prometheus text plus process invariant counters (internal auth)
- `/metrics.json` — invariant counter snapshot
- `deploy/base/prometheus-rules.yaml` — alert rules for financial-safety anomalies

---

## Credibility summary

| Layer | Claim | How proven |
|---|---|---|
| Trace-cap safety | No over-subscription under concurrency | `test_concurrent_reserves_respect_cap` on Postgres MVCC |
| Reconciler idempotency | No duplicate refunds | `test_concurrent_sweepers_no_duplicate_refunds` with SKIP LOCKED |
| Drift lockout | Wallet locked on policy breach | `test_drift_above_threshold_locks_wallet` |
| Late settlement | Correct correction debit after EXPIRED / STRANDED | Multiple tests in both tiers |
| Load invariants | No negative balances under 20-worker mixed load | `test_load_mixed_activity_no_negative_balances` |
| No cap overruns under load | Zero violations in hot-trace scenario | `test_load_hot_trace_contention_invariants` |
| Anomaly counters | Negative wallet, duplicate settlement/refund probes | `test_phase4_anomaly.py` |
| Admin reporting | Audit log, spend report, wallet summary behind internal auth | `test_phase4_reporting.py` |
| Orchestration plane | Standalone/co-existing workflow, critic, semantic cache | `test_orchestration_plane.py` |
