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

### Lightweight local checks

```bash
pytest -q tests/integration/test_ledger_hardening.py
pytest -q tests/load/test_load_harness.py
```

### Postgres-backed proof checks (real migrations)

```bash
export POSTGRES_TEST_URL=<postgres-test-url>
pytest -q tests/integration/test_postgres_reliability.py
```

### Generate machine-readable invariant report

```bash
python scripts/generate_invariant_report.py --operations 120 --workers 12
```

Output: `artifacts/reliability/latest_invariant_report.json`

See `docs/reliability-testing.md` for scope, scenarios, and interpretation notes.

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

artifacts/reliability/
docs/
gateway/
migrations/
reconciler/
scripts/
sidecar/
tests/
```

## Precision note

Load-harness outputs in this repository are correctness/invariant artifacts. They are intentionally not presented as universal throughput or latency claims.
