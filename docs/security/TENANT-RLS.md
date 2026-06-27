# Postgres Row-Level Security — tenant isolation (institutional++)

## TPRM answer

> Multi-tenancy is enforced at the **PostgreSQL engine** via Row-Level Security (RLS), not only `WHERE tenant_id = ?` in application code.

## Architecture

| Layer | Responsibility |
|-------|----------------|
| **OIDC JWT** | `tenant_id` claim validated with full JWKS signature verification (`auth_oidc.py`) — **never** `verify_signature=False` |
| **Session** | `SET LOCAL app.current_tenant_id` via `set_config(..., true)` inside transaction |
| **Pool** | `RESET ALL` on session teardown **and** on pool checkout (ghost-tenant leak prevention) |
| **Database** | `app_current_tenant_id()` SQL function; RLS policies on `escrow_ledger`, `ledger_events`, `guardrail_incidents` |

## Migration

`migrations/0013_tenant_rls.sql` — enable `FORCE ROW LEVEL SECURITY` for role `governor_app`.

Application DB user in production should be `governor_app`, not superuser.

## Safe coercion (no UUID cast trap)

Policies compare **VARCHAR tenant_id** to `app_current_tenant_id()` text. Invalid session values yield NULL → **zero rows** (deny), not Postgres cast exception.

## Application usage

```python
from sidecar.app.tenant_rls import tenant_scoped_session

with get_db_session() as session:
    with session.begin():
        with tenant_scoped_session(session, auth.tenant_id):
            # all queries scoped by RLS
            ...
```

## Verification benchmarks (due diligence)

| Test | Command |
|------|---------|
| Tenant ID validation | `pytest tests/integration/test_tenant_rls.py` |
| Cross-tenant leak (Postgres) | Run with `POSTGRES_TEST_URL` after migration 0013 |
| Pool reset | `install_pool_tenant_reset` on engine in `db.py` |

## Known limits

- RLS does not replace network segmentation or encryption at rest (RDS/KMS still required).
- Single-tenant pilots may use `default-tenant` with `rls_enabled=false` until multi-tenant pilot.

## Related

- [SHADOW-ENFORCE.md](SHADOW-ENFORCE.md)
- [THREAT-MODEL.md](THREAT-MODEL.md) (roadmap)
