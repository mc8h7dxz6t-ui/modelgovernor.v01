# modelgovernor.v01

A production-grade, ledger-backed AI governance control plane for reliable spend control, policy enforcement, and auditable reconciliation across multi-provider and agentic workloads.

## What this repository demonstrates

- Reserve-before-dispatch governance semantics
- Append-only ledger event trail for material state transitions
- Replay-safe reserve/settle lifecycle
- Per-trace atomic cap enforcement
- Drift enforcement with deterministic wallet lockout
- Reconciler handling for expiry, stranded holds, and late settlement
- Internal-auth operational read APIs for wallet/operation/trace/audit state
- Internal-auth Prometheus-style metrics at `/metrics`

## Quick local demo (Docker Compose first)

Prerequisites: Docker + Docker Compose plugin, `make`, `curl`.

```bash
make demo-up
make demo-smoke
make demo-drift-lock
make demo-status
```

Then inspect:

```bash
make demo-ledger
make demo-events
```

Internal operational surfaces (all require `x-internal-token`):

```bash
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/internal/wallet/demo-user
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/internal/events/recent?limit=20
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/metrics
```

Shutdown:

```bash
make demo-down
```

See `docs/demo.md` for full walkthrough and troubleshooting.

## Proof / reliability validation

Institutional++ **gold standard**: runtime anomaly probes, DB invariant backstops (`migrations/0005`–`0007`), Redis guardrails with graceful degradation, provider circuit breakers, OpenTelemetry-ready tracing, governance gateway, HTTP RED metrics, SLO burn-rate alerts, synthetic canary probes, property/chaos tests, and full K8s deploy manifests. See `docs/slo-definitions.md` and `docs/observability.md`.

Three tiers of testing are available. See `docs/reliability-testing.md` for full scenario tables, metrics reference, and CI integration examples.

### Tier 1 — Lightweight local checks (SQLite, < 1 second)

```bash
pytest -q tests/integration/test_ledger_hardening.py
pytest -q tests/programs/finance_ops_finals/
pytest -q tests/programs/cost_attribution_accountability/
```

### Tier 2 — Postgres vigorous proof (real DB semantics)

```bash
docker compose -f docker-compose.test.yml up -d postgres-test
export POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5433/mg_test
pytest -q tests/integration/test_postgres_vigorous.py
```

### Tier 3 — Load harness (SQLite or Postgres)

```bash
pytest -q tests/load/test_load_harness.py
# or run all scenarios and write a JSON report:
python tests/load/test_load_harness.py
```

Reports are written to `tests/load/reports/`.

### Production HA (Finance Ops Finals)

```bash
docker compose -f docker-compose.ha.yml up -d --scale sidecar=3 --scale reconciler=2
kustomize build deploy/overlays/production | kubectl apply --dry-run=client -f -
```

See `docs/ha-strategy.md`, `docs/pgbouncer-runbook.md`, `programs/finance_ops_finals/README.md`.

### Tier 4 — Toxiproxy chaos (Finance Ops, Postgres)

```bash
docker compose -f docker-compose.chaos.yml up -d
export POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5435/mg_chaos
pytest -q tests/chaos/test_toxiproxy_finance_ops.py
```

### Invariant report (optional)

```bash
python scripts/generate_invariant_report.py --operations 120 --workers 12
```

Output: `artifacts/reliability/latest_invariant_report.json`

## Command surface

```bash
make demo-up
make demo-down
make demo-reset
make demo-smoke
make demo-drift-lock
make demo-status
make demo-ledger
make demo-events
make proof-test
make load-test
```

## Diligence-oriented docs

- `LICENSE` (license posture)
- `docs/dependency-licenses.md` (dependency/license visibility)
- `docs/transferability.md` (portability and operational cleanliness)
- `docs/reliability-testing.md` (proof tiers and invariant artifacts)

## Repository layout

```text
README.md
LICENSE
Makefile
.env.example
docker-compose.yml
docker-compose.test.yml
docker-compose.ha.yml
docker-compose.chaos.yml

deploy/
  base/                 # K8s manifests, PgBouncer, migration job, Prometheus rules
  overlays/
    staging/
    production/
docs/
gateway/
migrations/
reconciler/
scripts/
sidecar/
  app/
    metrics.py          # invariant counter registry
tests/
  programs/
    finance_ops_finals/              # AI Finance Ops Finals for LLMs
    cost_attribution_accountability/ # AI Cost Attribution & Agent Accountability
  integration/
    conftest.py         # Postgres session fixtures
    test_postgres_vigorous.py
  load/
    test_load_harness.py
```

## Precision note

Load-harness outputs in this repository are correctness/invariant artifacts. They are intentionally not presented as universal throughput or latency claims.
