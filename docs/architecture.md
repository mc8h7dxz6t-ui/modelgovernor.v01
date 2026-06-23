# Architecture

## Overview

modelgovernor.v01 is a provider-agnostic AI governance control plane built to enforce institutional-grade controls across LLM workloads.

The platform separates model routing from governance state management:

- **LiteLLM gateway** normalizes and routes OpenAI-compatible requests across providers.
- **Policy sidecar** enforces request policy, budget reservation, settlement, and replay protection.
- **Policy sidecar** also exposes internal-auth operational surfaces for metrics and governance diligence reads.
- **Postgres** serves as the exact-decimal ledger and audit system of record.
- **Redis** provides volatile runtime guardrails such as trace depth, concurrency, and rate-limit counters.
- **Reconciler** claims expired work, expires safe holds, preserves stranded holds, and appends deterministic correction events.

## Primary differentiation

modelgovernor.v01 is designed around a ledger-backed reserve-before-dispatch control model. Its primary industry edge is Adaptive Reservation Sizing: a policy-bounded statistical reservation system that reduces unnecessary capital lock-up while preserving deterministic financial control and auditability.

## Supported operating modes

### Governed mode (gateway + sidecar)
- Gateway remains the request ingress for OpenAI-compatible workloads.
- Sidecar remains the enforcement and ledger transition authority.
- Postgres remains the governance system of record.

### Standalone mode (direct sidecar API)
- Clients call sidecar reserve/settle APIs directly.
- The same internal-auth, execution-identity, and ledger controls still apply.
- Postgres remains the governance system of record.

In both modes, the sidecar contract is the stable control-plane boundary. Governance metadata stays first-class and auditable independent of whether traffic arrived through gateway mediation or direct sidecar integration.

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
8. Sidecar enforces logical-operation idempotency using the request fingerprint and idempotency key.
9. Sidecar updates the authoritative `trace_budget_state` row atomically so concurrent reservations cannot oversubscribe a trace cap.
10. Sidecar debits the wallet, inserts a `RESERVED` ledger row, and appends a `RESERVE_CREATED` audit event in the same transaction.
10. Gateway dispatches upstream only after reservation commit succeeds.

### 2. In-flight execution
1. Gateway proxies the provider request.
2. Gateway records a provider dispatch attempt using a distinct `dispatch_attempt_key` and optional `provider_request_id`.
3. The logical operation transitions from `RESERVED` to `IN_FLIGHT`; timed-out or disconnected calls move to `PROVIDER_TIMEOUT`, not a false failure state.
4. Multiple provider attempts may exist beneath one logical operation when legitimate failover occurs.

### 3. Settlement
1. Gateway or callback path invokes sidecar settlement.
2. Sidecar resolves the logical operation by idempotency key or provider request id.
3. Sidecar locks the ledger row and verifies eligibility.
4. Sidecar computes final cost using authoritative provider usage when available.
5. Sidecar credits unused reserve or appends correction debits when authoritative spend exceeds the reserved amount.
6. Material positive drift appends deterministic anomaly events and locks the wallet pending review.
7. Late authoritative settlement after `STRANDED` or `EXPIRED` state is recorded as `RECONCILED_LATE_SETTLE`, preserving audit meaning instead of overwriting history.

### 4. Expiry and repair
1. Reconciler scans expiring rows in micro-batches and claims them with `FOR UPDATE SKIP LOCKED` on PostgreSQL.
2. Rows are claimed using `FOR UPDATE SKIP LOCKED`.
3. Never-dispatched `RESERVED` rows are refunded, transitioned to `EXPIRED`, and recorded with `EXPIRED_SWEEP`.
4. Expired `IN_FLIGHT` or `PROVIDER_TIMEOUT` rows become `STRANDED` so ambiguous provider outcomes retain their hold until an authoritative late settle or explicit correction arrives.
5. Reconciler never rewrites financial history; it only appends reason-coded events and applies deterministic balance corrections.

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

## Internal operational surfaces

All operational read and metrics routes are internal-auth protected with the same sidecar token gate used by mutation routes.

- `GET /metrics`: Prometheus-style counters/gauges derived from ledger and trace-budget system-of-record state.
- `GET /internal/wallet/{user_id}`: wallet balance and lock posture.
- `GET /internal/operation/{idempotency_key}`: logical operation state plus provider dispatch attempts.
- `GET /internal/operation/by-provider/{provider_request_id}`: provider-driven operation lookup.
- `GET /internal/trace/{trace_id}`: cap/reserved/settled trace budget state.
- `GET /internal/events/recent?limit=N`: most recent append-only audit events.

These routes are read-only and intentionally governance-oriented so operators can perform diligence without direct SQL access while preserving Postgres as the single source of truth.

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
- PgBouncer, RDS Proxy, or equivalent transaction-pooling proxy in front of Postgres
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
