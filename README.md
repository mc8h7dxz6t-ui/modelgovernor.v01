# modelgovernor.v01

modelgovernor.v01 is an institutional-grade AI governance control plane for organizations that require deterministic spend controls, enforceable model policy, exact ledger-backed accounting, and provider-agnostic routing across LLM workloads.

Its core differentiation is **Adaptive Reservation Sizing**: a policy-bounded capability that reduces unnecessary reserve lock-up while preserving reserve-before-dispatch enforcement, exact settlement, auditability, and conservative fail-safe behavior.

## Market positioning

Enterprise AI governance operates across three layers:

1. **Policy layer** — what is permitted
2. **Workflow layer** — who approves and what evidence exists
3. **Execution layer** — what can actually run, spend, settle, and be reconciled

modelgovernor.v01 is purpose-built for **layer 3**.

Most enterprise AI governance platforms focus primarily on policy inventories, approvals, governance workflows, evidence collection, or compliance mapping. Those systems are valuable, but they typically do not sit directly in the runtime execution path where financial control and request-time enforcement must actually occur.

modelgovernor.v01 is designed to complement those platforms by serving as the **runtime enforcement and financial governance control plane** for governed AI execution.

### Category distinctions

- **Enterprise governance system-of-record and workflow platforms** such as Credo AI, OneTrust, ServiceNow, and IBM watsonx.governance focus on inventory, approvals, assessments, and organizational governance workflows.
- **Fairness and compliance specialists** such as FairNow focus on fairness, transparency, and model-risk evidence workflows.
- **Policy accelerators and downloadable governance kits** provide templates, operating baselines, and policy packs.
- **modelgovernor.v01** focuses on deterministic runtime enforcement: reserve-before-dispatch budget control, exact-decimal settlement, bounded request-time policy enforcement, reconciliation, and audit-grade financial lineage.

## What it does

modelgovernor.v01 combines:
- an OpenAI-compatible gateway layer,
- a hardened policy sidecar,
- a Postgres-backed escrow and audit ledger,
- Redis-based volatile runtime guardrails,
- and a reconciler for stale reservation repair.

This architecture supports a portable path from laptop development to VPS deployment to hardened enterprise environments.

## Why it is different

Most gateways focus on model routing, logging, or provider abstraction. modelgovernor.v01 is built around a stricter control objective:

- reserve approved spend before provider dispatch,
- settle exact realized usage after execution,
- return unused capital deterministically,
- enforce model and request policy centrally,
- and provide audit-grade lineage for all financial state transitions.

On top of that base, Adaptive Reservation Sizing improves capital efficiency by replacing static worst-case reservation behavior with policy-bounded statistical reservation recommendations and conservative fallback under drift.

## Core capabilities

- OpenAI-compatible multi-provider gateway
- Strict model policy registry
- Reserve-before-dispatch spend controls
- Postgres-backed exact-decimal ledger
- Append-only audit trail
- Replay-safe idempotency controls
- Adaptive Reservation Sizing with conservative fallback
- Bounded uplift for approved workloads
- Runtime trace and concurrency guardrails
- Deterministic stale-reservation reconciliation
- Portable Docker-first deployment

## Architecture overview

modelgovernor.v01 is built as a layered control plane:

1. **Gateway layer** using LiteLLM for provider normalization and routing.
2. **Policy sidecar** for reserve, uplift, settle, refund, and policy enforcement workflows.
3. **Postgres ledger** as the system of record for balances, reservations, settlements, and audit events.
4. **Redis guardrails** for volatile trace depth, concurrency, and short-window control counters.
5. **Reconciler worker** for stale reservation cleanup, drift support workflows, and operational repair.

## Institutional-grade design principles

- Provider-agnostic routing through a centralized gateway
- Strict model allowlists and policy registry enforcement
- Reserve-before-dispatch cost controls
- Exact decimal ledger accounting in PostgreSQL
- Append-only audit event history
- Idempotent settlement and replay protection
- Conservative fallback when adaptive confidence degrades
- Runtime guardrails for traces, concurrency, and request velocity
- Deterministic reconciliation for stale reservations
- Portable deployment across local, VPS, and cloud environments

## Engineering standards

To maintain institutional-grade behavior as throughput grows, the platform is designed around the following constraints:

- **Short, indexed reserve transactions** to keep reservation latency predictable under concurrency
- **Database-enforced idempotency** so retries cannot double-lock capital
- **Dedicated volatile guardrail memory** so Redis eviction cannot corrupt runtime enforcement
- **Provider-aware final settlement** so authoritative usage metadata remains preferred when available
- **Conservative degraded-mode behavior** so the platform fails safe when dependencies or telemetry are impaired

These constraints ensure the system remains credible not just in architecture diagrams, but in operational reality.

## Repository layout

```text
README.md
.env.example
docker-compose.yml

docs/
  adaptive-reservation.md
  architecture.md
  build-plan.md

gateway/
  litellm.config.yaml
  README.md

migrations/
  0001_init.sql
  0002_seed_model_policy.sql

sidecar/
  Dockerfile
  requirements.txt
  app/
    main.py
    config.py
    schemas.py
    auth.py
    db.py
    policy.py
    routes_reserve.py
    routes_settle.py

reconciler/
  Dockerfile
  requirements.txt
  app/
    main.py
    db.py
    sweeper.py

tests/
  integration/
  fixtures/
```

## Development roadmap

### Phase 1
- Monorepo scaffold
- Docker Compose local stack
- Postgres schema and seed policies
- Sidecar reserve and settle APIs
- Reconciler daemon
- LiteLLM gateway configuration

### Phase 2
- Adaptive Reservation Sizing shadow mode
- Drift telemetry and conservative fallback controls
- Internal auth hardening between gateway and sidecar
- Structured metrics and alerts
- Provider request ID capture

### Phase 3
- Tenant-scoped adaptive mode rollout
- Bounded uplift for approved workloads
- Provider optimization under strict policy constraints
- Admin and reporting workflows

## Quickstart goals

The initial scaffold is designed to support:
- one-command local startup,
- exact-decimal schema initialization,
- sidecar service development,
- reconciler development,
- and later CI validation once the service skeletons are in place.

## Status

Repository scaffold is being built on branch `copilot/scaffold-institutional-v1`.
