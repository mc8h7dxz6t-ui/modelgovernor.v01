# Architecture

## Overview

modelgovernor.v01 is a provider-agnostic AI governance control plane built to enforce institutional-grade controls across LLM workloads.

The platform separates model routing from governance state management:

- **LiteLLM gateway** normalizes and routes OpenAI-compatible requests across providers.
- **Policy sidecar** enforces request policy, budget reservation, settlement, and replay protection.
- **Postgres** serves as the exact-decimal ledger and audit system of record.
- **Redis** provides volatile runtime guardrails such as trace depth, concurrency, and rate-limit counters.
- **Reconciler** expires stale reservations and restores balances deterministically.

## Primary differentiation

modelgovernor.v01 is designed around a ledger-backed reserve-before-dispatch control model. Its primary industry edge is Adaptive Reservation Sizing: a policy-bounded statistical reservation system that reduces unnecessary capital lock-up while preserving deterministic financial control and auditability.

## Trust boundaries

- Application and agent workloads do not call providers directly.
- All governed inference must pass through the gateway and policy sidecar.
- Financial state transitions occur only inside Postgres transactions.
- Redis is never the source of truth for balances or reservations.
- Final settlement uses authoritative provider usage where available.

## Request lifecycle

### 1. Reserve before dispatch
1. Client sends OpenAI-compatible request to the gateway.
2. Gateway forwards request metadata to the policy sidecar.
3. Sidecar validates internal auth, request schema, tenant context, and policy allowlists.
4. Sidecar checks Redis-based volatile guardrails if enabled.
5. Sidecar selects conservative or adaptive reservation mode.
6. Sidecar estimates reserve requirement.
7. Sidecar opens a Postgres transaction.
8. Sidecar enforces idempotency using the request fingerprint and idempotency key.
9. Sidecar locks the wallet row, debits available balance, inserts a `RESERVED` ledger row, and appends a `RESERVE_CREATED` audit event.
10. Gateway dispatches upstream only after reservation commit succeeds.

### 2. In-flight execution
1. Gateway proxies the provider request.
2. Streaming or long-running calls may be monitored using provider-aware output growth estimation.
3. If policy permits and projected usage threatens to exhaust reserve headroom, the sidecar may attempt a bounded uplift transaction.
4. If uplift is denied, the gateway terminates upstream execution and records a governed termination event.

### 3. Settlement
1. Gateway or callback path invokes sidecar settlement.
2. Sidecar loads the ledger row by idempotency key.
3. Sidecar locks the ledger row and verifies eligibility.
4. Sidecar computes final cost using authoritative provider usage when available.
5. Sidecar credits unused balance, marks the row `SETTLED`, and appends `SETTLED_FINAL` and drift events.

### 4. Expiry and repair
1. Reconciler scans for expired `RESERVED` rows in micro-batches.
2. Rows are claimed using `FOR UPDATE SKIP LOCKED`.
3. Reconciler refunds balance, marks the row `EXPIRED`, and appends an `EXPIRED_SWEEP` event.

## Core control invariants

- No direct provider egress from application or agent subnets
- Allowlisted models only
- Hard input, output, timeout, and cost ceilings
- Idempotency key required for all governed requests
- Reserve before dispatch
- Postgres as sole financial source of truth
- Idempotent settlement and replay protection
- Append-only audit trail for all state transitions
- Deterministic reconciliation of stale reservations
- Conservative fallback when adaptive confidence degrades

## Adaptive Reservation Sizing

Adaptive Reservation Sizing is the platform's capital-efficiency layer.

Key properties:
- policy-bounded statistical reserve recommendations
- confidence-based reserve sizing per qualified cohort
- conservative fallback under sparse history or high drift
- bounded uplift for approved workloads only
- auditable reserve-versus-realized drift measurement

See `docs/adaptive-reservation.md` for the full specification.

## Deployment modes

### Local development
- Docker Compose
- LiteLLM gateway
- FastAPI sidecar
- Postgres
- Redis
- Reconciler worker

### Production baseline
- Container orchestration platform
- Managed or HA Postgres
- Redis for runtime counters only
- Private networking between gateway and sidecar
- Secrets managed externally
- Structured logs and metrics

## Portability principles

The platform is designed to remain portable across:
- macOS development laptops
- Linux servers and VPS deployments
- cloud container platforms
- Kubernetes clusters
- hybrid enterprise environments

Portability is achieved by keeping the core stack limited to:
- OpenAI-compatible HTTP contracts
- LiteLLM
- FastAPI
- PostgreSQL
- Redis
- Docker-first packaging
