# Build Plan

## Goal

Deliver a portable, institutional-grade AI governance gateway that can be reproduced on a laptop and hardened for enterprise deployment.

## Phase 1: portable baseline

### Deliverables
- Monorepo scaffold
- Docker Compose stack
- Postgres schema and seed policies
- Sidecar reserve endpoint
- Sidecar settle endpoint
- Reconciler daemon
- LiteLLM gateway configuration
- README and architecture docs

### Success criteria
- Local environment boots with a single Docker Compose command
- Policy sidecar can reserve and settle requests end to end
- Expired reservations are reclaimed automatically
- Model allowlists and request caps are enforced through database-backed policy

## Phase 2: production hardening

### Deliverables
- Internal auth hardening between gateway and sidecar
- Per-trace spend caps
- Structured metrics and alerts
- Provider request ID capture
- Degraded-mode policies
- Integration test coverage for failure paths

### Success criteria
- Replay protection validated through tests
- Reconciler operates safely under concurrent execution
- Audit events capture all terminal ledger transitions
- Operational alerts exist for reserve failures, settle anomalies, and reconciliation drift

## Phase 3: enterprise expansion

### Deliverables
- Provider reconciliation workflows
- Admin workflows for manual adjustments
- Reporting exports and anomaly summaries
- Deployment automation for container platforms
- Optional HA and multi-region strategy documentation

### Success criteria
- Correction workflows are captured in append-only audit events
- Provider-side discrepancies can be surfaced and resolved deterministically
- Deployment artifacts support repeatable installation across environments

## Build order

1. Repository documentation
2. SQL migrations
3. Docker Compose and environment configuration
4. Sidecar application skeleton
5. Reconciler worker skeleton
6. Gateway configuration
7. Integration test scaffolding

## Non-goals for initial scaffold

- Multi-region replication
- Provider invoice sync on day one
- Full admin UI
- Advanced analytics or dashboards

These are deferred until the portable baseline is stable and verified.
