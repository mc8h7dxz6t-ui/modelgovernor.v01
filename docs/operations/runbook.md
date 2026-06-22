# Operations Runbook

## Scope

This runbook defines incident response procedures for governance-critical operational signals in `modelgovernor.v01`.

## Core signals

- `sidecar_reserve_requests_total` by `outcome`
- `sidecar_settle_requests_total` by `outcome`
- `sidecar_reserve_amount_dollars_total`
- `sidecar_settle_amount_dollars_total`
- reconciliation mismatch backlog from `GET /admin/reconciliation-summary`

## Alert handling

### Reserve error alert

1. Confirm sidecar readiness (`/readyz`) and liveness (`/healthz`) for all replicas.
2. Confirm Postgres health and connection saturation.
3. Confirm Redis availability and error rates.
4. If sidecar is healthy but DB unavailable, route incident to database on-call and keep fail-closed posture.
5. Verify reserve path recovery before closing incident.

### Settle error alert

1. Confirm sidecar readiness and DB write health.
2. Inspect settlement failure logs for repeated idempotency collisions versus backend unavailability.
3. Verify wallet refunds and `SETTLED_FINAL` events are still emitted for recovered traffic.
4. Validate replay behavior by retrying a recent settled idempotency key.

### Settlement drift alert

1. Compare reserve/settle throughput panel and recent deploy history.
2. Query `GET /admin/reconciliation-summary` for unresolved mismatches.
3. Run provider reconciliation workflow for the impacted window.
4. If mismatches remain, run admin correction workflow and record incident reference.

## Reconciler lag response

1. Confirm reconciler pod is healthy and processing sweeps.
2. Check `RECONCILER_INTERVAL_SECONDS` and `RECONCILER_BATCH_SIZE` for current environment overlay.
3. Increase batch size or reduce interval only after confirming Postgres lock behavior remains healthy.

## Release and rollback posture

- Apply migrations before rolling sidecar image updates.
- Use rolling updates for sidecar and single-replica reconciler replacement.
- Roll back images using the previous signed release tag.
- Re-run reconciliation summary checks after rollback to confirm no ledger drift.

## HA/DR checkpoints

- Validate synchronous replication posture for Postgres primary/standby.
- Validate PITR retention and last successful backup.
- Confirm regional routing sends traffic to local stack only.
