# High-Availability and Multi-Region Strategy

## Overview

modelgovernor.v01 is designed for horizontal scale and operational resilience.
This document describes the recommended HA deployment topology and the
constraints that govern safe multi-region operation.

---

## Single-region HA baseline

### Sidecar scaling

The policy sidecar is stateless at the application layer.  All governance state
lives in Postgres.  Multiple sidecar pods can run in parallel without
coordination, subject to the following conditions:

- Postgres is the sole financial source of truth.
- All balance mutations use atomic `UPDATE ... RETURNING` or `FOR UPDATE`
  row-locking to prevent concurrent reservation races.
- Application-side connection pools should be intentionally small (3–5
  connections per pod) with a transaction-pooling proxy (PgBouncer, RDS Proxy,
  or Cloud SQL Auth Proxy) in front.  A large unconstrained pool bypasses the
  proxy's concurrency controls and drives unnecessary Postgres contention.

Recommended minimum: **3 sidecar replicas** behind a load balancer with
`maxSurge=1` and `maxUnavailable=0` for zero-downtime rolling updates.

### Reconciler concurrency

The reconciler uses `FOR UPDATE SKIP LOCKED` when sweeping expired
reservations.  Multiple reconciler pods can therefore run simultaneously
without duplicate refunds or double-expiry.  However, the standard deployment
uses a `CronJob` with `concurrencyPolicy: Forbid` to keep operational
behaviour predictable and cost-efficient.  A redundant standby reconciler
can be enabled using a separate CronJob with a slightly offset schedule
(e.g., one at `*/2 * * * *` and a hot standby at `1-59/2 * * * *`) to
halve recovery time after a pod failure.

### Postgres HA

Use a managed Postgres service (RDS Multi-AZ, Cloud SQL HA, or Azure Database
for PostgreSQL with zone-redundant HA) or a self-managed cluster with
synchronous replication (Patroni + etcd, or Crunchy PostgreSQL Operator).

Key settings:
- `synchronous_standby_names = '*'` for synchronous replication when RPO = 0
  is required.
- WAL archiving to durable object storage (S3, GCS) for point-in-time
  recovery.
- Connection timeout and pool recycle settings in the sidecar must account for
  brief failover windows (~30 s for managed services).  Use `pool_pre_ping=True`
  (already configured) and a `pool_recycle` no longer than half the managed
  service's idle connection timeout.

### Redis HA

Redis is used only for volatile runtime guardrails (trace depth, concurrency
counters, rate-limit windows).  It is not the financial source of truth.
A Redis Sentinel cluster or Elasticache Multi-AZ replication group provides
sufficient resilience.  Loss of Redis during a failure window degrades runtime
guardrail enforcement but does not corrupt the Postgres ledger.

---

## Multi-region strategy

### Constraint: single-writer Postgres

The reserve-before-dispatch control model requires atomic balance deductions.
Two geographically separated Postgres instances cannot provide linearisable
balance mutations without a distributed transaction protocol.  **Do not run
active-active Postgres replication for the escrow ledger across regions.**

The recommended multi-region topology is **active-passive** for the ledger:

```
Region A (active)                Region B (passive / DR)
─────────────────                ──────────────────────────
  Sidecar × N                      Sidecar × N  (read-only
  Reconciler (CronJob)               health probe only)
  Postgres primary          ←──      Postgres standby (streaming)
  Redis cluster                      Redis cluster
  PgBouncer / proxy                  PgBouncer / proxy (points to
                                     primary in A or promoted
                                     standby in B)
```

During normal operation:
- All write traffic is routed to Region A.
- Region B sidecars run in a degraded-mode that returns 503 for all reserve
  requests, directing clients to Region A.
- Region B Postgres standby receives streaming replication from A and is
  available for read-only diagnostic queries.

During failover:
1. The managed Postgres service or Patroni promotes the Region B standby.
2. PgBouncer in Region B is reconfigured to point to the promoted primary.
3. Region B sidecars exit degraded mode and accept write traffic.
4. DNS or the load balancer directs client traffic to Region B.
5. After Region A recovers it rejoins as the new standby until a planned
   failback is scheduled.

### RPO and RTO targets

| Tier | RPO | RTO | Notes |
|---|---|---|---|
| Managed Postgres Multi-AZ | ~0 s | 30–60 s | Managed failover |
| Postgres + Patroni HA | ~0 s (sync) | 10–30 s | Depends on cluster config |
| Cross-region DR (streaming) | seconds to minutes | 5–15 min | Manual or semi-automated |

### Trace-cap consistency across regions

`trace_budget_state` rows are written by the authoritative Region A primary.
During a cross-region failover, in-flight trace-cap operations may need to be
re-verified by the reconciler on Region B once it becomes active.  The
reconciler's STRANDED transition handles this: operations that were
`IN_FLIGHT` at failover time become STRANDED and are resolved via normal
admin correction or late settlement paths.

---

## Deployment portability

The Kubernetes manifests in `deploy/base` and `deploy/overlays/{staging,production}`
support deployment to any Kubernetes 1.25+ cluster.  The only external
dependencies are:

- A Postgres 14+ instance reachable from within the cluster.
- A Redis 6+ instance or cluster.
- A Kubernetes `Secret` named `modelgovernor-secrets` containing:
  - `database-url` — full Postgres connection URL (via PgBouncer in production)
  - `redis-url` — Redis connection URL
  - `sidecar-internal-tokens` — comma-separated list of allowed internal tokens

See `deploy/base/secrets.example.yaml` for a template. Secrets are never stored
in the repository.  Use a secrets manager (AWS
Secrets Manager, GCP Secret Manager, HashiCorp Vault, or sealed-secrets) to
inject them at deploy time.

---

## Operational runbook references

See `docs/operations-runbook.md` for startup order, rollout checks, observability
expectations, and recovery playbooks that complement this HA guidance.

| Scenario | Resolution |
|---|---|
| Sidecar pod OOMKilled | Increase memory limit in overlay patch; investigate Postgres query plan |
| Reconciler not sweeping | Check CronJob history; confirm DATABASE_URL is set; review Postgres connectivity |
| STRANDED operations accumulating | Run `GET /internal/operations?status=STRANDED`; resolve via internal correction flows |
| Wallet locked by drift enforcement | Investigate provider invoice; review wallet via `GET /internal/wallet/{user_id}` |
| Postgres failover | Confirm PgBouncer / proxy points to new primary; restart sidecar pods to flush stale connections |
| Redis unavailable | Sidecar continues to operate for reserve/settle (no hard Redis dependency in core paths); runtime guardrails are degraded |
