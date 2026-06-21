# Adaptive Reservation Sizing

Adaptive Reservation Sizing is the capital-efficiency layer for modelgovernor.v01.

## Objective

Reduce idle reservation lock-up while preserving reserve-before-dispatch controls, deterministic settlement, and audit-grade lineage.

## Guardrails

- Postgres remains the sole financial source of truth.
- Adaptive mode is policy-bounded and tenant-scoped.
- Sparse-history cohorts default to conservative reservation behavior.
- Bounded uplift is optional and policy-gated.
- Drift automatically triggers conservative fallback.

## Lifecycle alignment

1. Sidecar computes reserve estimate under policy bounds.
2. Sidecar reserves funds in a single ledger transaction before dispatch.
3. Settlement writes exact realized usage and releases surplus deterministically.
4. Reconciler expires stale reservations with `FOR UPDATE SKIP LOCKED` workflows.
5. Audit events capture reserve, uplift, settle, and expiry transitions.

## Rollout posture

- Start in shadow mode with recommendation-only telemetry.
- Move to active mode per tenant after drift thresholds pass.
- Automatically revert to conservative mode when confidence degrades.
