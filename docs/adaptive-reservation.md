# Adaptive Reservation Sizing

## Purpose

Adaptive Reservation Sizing is the capital-efficiency layer of modelgovernor.v01.
It reduces unnecessary reserve lock-up while preserving deterministic,
policy-enforced, ledger-backed controls.

## Cohort definition

Adaptive behavior is enabled only for approved cohorts keyed by:

- tenant or wallet segment
- model
- workload class (request shape / route family)
- bounded policy profile

A cohort is eligible only when sufficient historical settlement data exists and
drift quality remains within policy tolerance.

## Confidence-interval sizing

For an eligible cohort, reserve sizing uses a conservative confidence interval
over historical realized cost:

- central estimate from stable trailing history
- uncertainty margin from cohort variance and sample count
- reserve recommendation = central estimate + confidence margin

The recommendation is always clamped by hard policy ceilings and minimum
reserve floors.

## Conservative fallback triggers

Adaptive mode is disabled for a cohort when any trigger is met:

- insufficient sample count
- recent drift volatility above threshold
- repeated anomalous settlement behavior
- policy/profile change invalidating prior history

Fallback mode uses deterministic conservative reservation configured by policy
until cohort quality recovers.

## Bounded-uplift approval model

Adaptive reservation cannot silently expand financial risk:

- each cohort has an explicit maximum uplift bound relative to conservative mode
- uplift requires prior approval in policy configuration
- reserve decisions above the bound are rejected and fall back to conservative

This preserves institutional governance while still improving capital
efficiency for proven workloads.

## Drift measurement methodology

Drift is measured per operation as:

- `drift_amount = actual_settlement_cost - reserved_amount`

Operational interpretation:

- negative/zero drift: reserve covered spend with no deficit
- positive drift: authoritative provider cost exceeded reserve

Control behavior:

- tolerated drift is logged with `DRIFT_TOLERATED`
- excessive drift is enforced with `DRIFT_ENFORCED` and wallet lock
- metrics counters and audit events provide deterministic observability

## Governance guarantees

Adaptive Reservation Sizing does not weaken core invariants:

- reserve-before-dispatch remains mandatory
- Postgres remains the system of record
- settlement remains idempotent
- all material transitions remain append-only auditable
- anomaly paths remain recoverable through reconciler and admin workflows
