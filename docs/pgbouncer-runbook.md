# PgBouncer Operations Runbook

## Role in Finance Ops Finals

PgBouncer sits between sidecar/reconciler pods and Postgres, providing **transaction pooling** so each pod keeps a small application pool (3–5 connections) without opening hundreds of direct Postgres backends.

## Configuration

- Config: `config/pgbouncer.ini`
- Pool mode: `transaction` (required for SQLAlchemy session-per-request)
- Listen port: `6432`
- `server_reset_query = DISCARD ALL` clears session state between transactions

## Connection strings

**Through PgBouncer (production):**

```text
postgresql+psycopg://postgres:PASSWORD@pgbouncer:6432/modelgovernor
```

**Direct Postgres (migrations only):**

```text
postgresql+psycopg://postgres:PASSWORD@postgres:5432/modelgovernor
```

Run schema migrations against the **primary Postgres** endpoint, not through PgBouncer transaction pooling, when using advisory locks or long-lived sessions.

## Local HA rehearsal

```bash
docker compose -f docker-compose.ha.yml up -d --scale sidecar=3 --scale reconciler=2
```

Verify:

```bash
curl -sf http://localhost:8081/readyz
curl -sf http://localhost:8082/healthz
```

## Kubernetes

Manifests: `deploy/base/pgbouncer.yaml`

- 2 PgBouncer replicas behind ClusterIP service `pgbouncer:6432`
- `modelgovernor-secrets/database-url` should target PgBouncer in production overlays

## Sizing guidance

| Workload | `default_pool_size` | `max_client_conn` |
|---|---|---|
| Dev / staging | 10 | 200 |
| Production (3–10 sidecars) | 20 | 500 |
| High traffic (10+ sidecars) | 30–50 | 1000 |

## Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `server login failed` | userlist mismatch | Sync `config/pgbouncer-userlist.txt` with Postgres credentials |
| Connection storms | pool too small | Increase `default_pool_size`; verify sidecar `DB_POOL_SIZE` ≤ pool per pod budget |
| Prepared statement errors | wrong pool mode | Ensure `pool_mode = transaction`, not session |
| Migration failures via pool | DDL through transaction pool | Run migrations direct to Postgres primary |

## Monitoring

Watch PgBouncer stats (`SHOW POOLS`, `SHOW STATS`) and correlate with sidecar `pool_timeout` errors and Postgres `active_connections`.
