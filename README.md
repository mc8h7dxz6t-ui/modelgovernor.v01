# modelgovernor.v01

A production-grade, ledger-backed AI governance control plane for reliable spend control, policy enforcement, and auditable reconciliation across multi-provider and agentic workloads.

## Supported operating modes

- **Governed mode**: gateway + sidecar + ledger controls, where governed inference is mediated through gateway contracts and sidecar enforcement.
- **Standalone mode**: direct sidecar API integration (no gateway in the request path), while retaining reserve/settle governance controls and auditability.

The **sidecar API is the stable integration boundary** in both modes. Governance metadata (`tenant_id`, `session_id`, `agent_run_id`, `workflow_step`) is required in headers, and can be mapped from either gateway traffic or standalone callers.

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

## Standalone quickstart (direct sidecar API)

Use this path when you want sidecar governance controls without routing through the gateway.

### Minimal runtime config

- `DATABASE_URL`
- `REDIS_URL`
- `SIDECAR_INTERNAL_TOKENS`
- request headers:
  - `x-internal-token`
  - `x-tenant-id`
  - `x-session-id`
  - `x-agent-run-id`
  - `x-workflow-step`

### Local SQLite/test path

Integration tests run sidecar directly with SQLite (`tests/integration/test_sidecar_admin_observability.py`) for portable standalone validation.

### Docker Compose/Postgres path

`make demo-up` is the standalone/local evaluation runtime path in this repository (sidecar + reconciler + Postgres + Redis). It does not currently run the gateway container.

### Direct reserve + settle example

```bash
curl -X POST http://localhost:8081/reserve \
  -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" \
  -H "x-tenant-id: tenant-demo" \
  -H "x-session-id: session-demo" \
  -H "x-agent-run-id: run-demo" \
  -H "x-workflow-step: step-1" \
  -H "content-type: application/json" \
  -d '{
    "user_id":"demo-user",
    "trace_id":"trace-standalone-1",
    "idempotency_key":"op-standalone-1",
    "model":"gpt-4o-mini",
    "estimated_cost":"1.000000"
  }'

curl -X POST http://localhost:8081/settle \
  -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" \
  -H "x-tenant-id: tenant-demo" \
  -H "x-session-id: session-demo" \
  -H "x-agent-run-id: run-demo" \
  -H "x-workflow-step: step-1" \
  -H "content-type: application/json" \
  -d '{
    "idempotency_key":"op-standalone-1",
    "outcome":"SETTLED",
    "actual_cost":"0.900000"
  }'
```

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
