# AI Finance Ops Finals for LLMs

Institutional++ settlement, reconciliation, and finance-plane invariant program with **production HA**.

## Scope

- Reserve → dispatch → settle finalization
- Drift enforcement and wallet lockout
- Reconciler expiry, stranded holds, late settlement
- Session-wide finance invariant audit (`sidecar/app/finance_ops.py`)

## Production HA stack

| Component | Implementation |
|---|---|
| Sidecar scale-out | Stateless replicas behind load balancer (3+ in production overlay) |
| PgBouncer | Transaction pooling (`config/pgbouncer.ini`, `deploy/base/pgbouncer.yaml`) |
| Reconciler leader election | Postgres `pg_try_advisory_lock` (`reconciler/app/leader.py`) |
| Reconciler daemon | Long-running sweep loop + `/healthz` `/readyz` on :8082 |
| Standby reconciler | Offset CronJob (`reconciler-standby` in K8s manifests) |
| Network chaos | Toxiproxy harness (`docker-compose.chaos.yml`, `tests/chaos/`) |
| Kubernetes | `deploy/base/` + `deploy/overlays/{staging,production}` |
| Promotion gate | `.github/workflows/promote.yml` |

## Local commands

```bash
# Core program tests
pytest -q tests/programs/finance_ops_finals/

# HA rehearsal (PgBouncer + scaled replicas)
docker compose -f docker-compose.ha.yml up -d --scale sidecar=3 --scale reconciler=2

# Toxiproxy chaos (Tier 4)
docker compose -f docker-compose.chaos.yml up -d
POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5435/mg_chaos \
  pytest tests/chaos/test_toxiproxy_finance_ops.py -q

# Kubernetes dry-run
kustomize build deploy/overlays/production | kubectl apply --dry-run=client -f -
```

## Docs

- `docs/ha-strategy.md` — multi-region, sidecar scaling, reconciler concurrency
- `docs/pgbouncer-runbook.md` — pool sizing and connection strings
- `docs/operations-runbook.md` — incident response and recovery

## Key invariants

| Invariant | Enforcement |
|---|---|
| No negative wallet balances | Runtime probe + `assert_finance_ops_invariants` |
| No trace cap overrun | Atomic UPDATE + DB CHECK (Postgres) |
| No duplicate refunds/settlements | Event probes + unique indexes (Postgres) |
| Single active reconciler leader | Postgres advisory lock |
| Survives network latency/timeouts | Toxiproxy chaos tests |
