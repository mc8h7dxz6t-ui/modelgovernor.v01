# modelgovernor.v01

## Institutional-Grade AI Governance Gateway

Reliable, robust, and policy-enforced multi-provider LLM control with auditable ledger-backed accounting and deterministic spend governance.

modelgovernor.v01 is an institutional-grade AI governance gateway for organizations that require strict spend control, enforceable model policy, auditable ledger-backed accounting, and provider-agnostic multi-provider routing.

It combines:
- an OpenAI-compatible gateway layer,
- a hardened policy enforcement sidecar,
- a Postgres-backed escrow and audit ledger,
- Redis-based runtime guardrails,
- and portable local-to-production deployment.

The system is designed to support serious governance standards for AI infrastructure across laptops, VPS deployments, cloud environments, and enterprise platforms.

## Core capabilities

- OpenAI-compatible multi-provider gateway
- Strict model policy registry covering all industry-leading providers
- Reserve-before-dispatch spend controls
- Postgres-backed escrow ledger
- Append-only audit trail
- Replay-safe idempotency controls
- Runtime trace and concurrency guardrails
- Deterministic stale-reservation reconciliation
- Provider reconciliation and admin correction workflows
- Reconciliation anomaly reporting
- Portable Docker-first and Kubernetes deployment

## Architecture overview

modelgovernor.v01 is built as a layered control plane:

1. **Gateway layer** using LiteLLM for provider normalization and routing.
2. **Policy sidecar** for reserve, settle, refund workflows and policy enforcement.
3. **Postgres ledger** as the system of record for balances, reservations, and audit events.
4. **Redis guardrails** for trace depth, concurrency controls, and short-window rate limits.
5. **Reconciler worker** for stale reservation cleanup and operational repair.

## Institutional-grade design principles

- Provider-agnostic routing through a centralized gateway
- Strict model allowlists and policy registry enforcement
- Reserve-before-dispatch cost controls
- Exact-decimal ledger accounting in PostgreSQL
- Append-only audit event history
- Idempotent settlement and replay protection
- Runtime guardrails for traces, concurrency, and request velocity
- Deterministic reconciliation for stale reservations
- Portable deployment across local, VPS, and cloud environments

## Repository layout

```text
README.md
.env.example
docker-compose.yml

deploy/
  kustomization.yaml
  namespace.yaml
  configmap.yaml
  sidecar-deployment.yaml
  sidecar-service.yaml
  reconciler-deployment.yaml
  migration-job.yaml

docs/
  architecture.md
  build-plan.md
  quality-bar.md
  adaptive-reservation.md
  operations/runbook.md
  observability/prometheus-rules.yaml
  observability/grafana-dashboard-modelgovernor.json

gateway/
  litellm.config.yaml
  README.md

migrations/
  0001_init.sql
  0002_seed_model_policy.sql
  0003_harden_ledger_constraints.sql
  0004_phase2_hardening.sql
  0005_phase3_reconciliation.sql
  0006_expand_model_policy.sql
  0007_governance_tiers.sql

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
    metrics.py
    routes_reserve.py
    routes_settle.py
    routes_reconcile.py

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
- Metrics and alerts
- Per-trace spend caps
- Provider request ID capture
- Hardened degraded-mode policies
- Admin workflows and operational tooling

### Phase 3
- Provider reconciliation and admin correction workflows
- Reconciliation anomaly reporting and summary endpoint
- Kubernetes deployment manifests with kustomize support
- HA and multi-region deployment strategy documentation

### Phase 4 (Platform Operations Maturity)
- Environment overlays for staging and production
- Kubernetes hardening objects (HPA, PDB, ingress, and network policies)
- Release and promotion workflows for image publication and gated rollout
- Live-stack smoke tests with real Postgres and Redis
- Observability assets (Prometheus alert rules, dashboard baseline, and runbook)

## Quality standard

All changes should meet the repository quality bar in `docs/quality-bar.md`.

## Status

Phase 3 complete. Provider reconciliation workflows, admin correction workflows, reporting endpoints, Kubernetes deployment artifacts, and HA documentation are in place.

Phase 4 platform-operations maturity baseline is now in progress with Kubernetes hardening objects, overlays, release/promotion workflows, live-stack smoke tests, and operational observability assets included in-repo.

Model policy registry covers all industry-leading providers: OpenAI, Anthropic, Google, Meta (via Groq), Mistral AI, Cohere, DeepSeek, and xAI. Each model carries explicit governance parameters — token caps, cost ceilings, stream permissions, and fallback pricing — applied uniformly across providers.

Governance tier classification (BUDGET / STANDARD / FRONTIER) is enforced at the schema level with per-tier `max_cost_per_trace` ceilings (25 / 50 / 150) and a CHECK constraint. Reasoning models enforce `stream_allowed = FALSE` for deterministic audit coverage. The full governed registry is inspectable at `GET /admin/models`.
