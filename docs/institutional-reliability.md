# Institutional++ reliability architecture

This document describes the production reliability model for ModelGovernor — the mechanisms that keep the finance control plane correct under failure, and how they compose.

## Design principles

1. **Postgres is authoritative** — Redis, in-memory state, and circuit breakers are acceleration layers only.
2. **Fail closed on money, fail open on reads** — diagnostic mode halts writes but keeps admin read APIs alive for recovery.
3. **Symmetric degradation** — when Redis fails, guardrails *and* circuit breakers fall back to per-pod in-memory limits (not unbounded bypass).
4. **Tamper-evident audit** — ledger events and privileged admin actions are hash-chained; hourly verification + anchor CronJobs detect drift.
5. **Single-writer reconciliation** — Postgres advisory locks elect one reconciler leader; sweeps are idempotent.

## Reliability stack

```
                    ┌─────────────────────────────────────┐
  Ingress           │  Gateway / governed dispatch        │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
  Policy plane      │  Sidecar (3+ replicas, HPA, PDB)    │
                    │  • Redis guardrails + local fallback │
                    │  • Circuit breaker + local fallback  │
                    │  • Diagnostic write halt             │
                    │  • OIDC RBAC on /internal/*          │
                    └──────────────┬──────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
    PgBouncer                 Redis HA                 OTEL / Prometheus
         │                         │
         ▼                         │
    Postgres ledger ◄──────────────┘ diagnostic mode pub/sub
         ▲
         │
    Reconciler (2 replicas, leader election)
    • expired / stranded sweeps
    • post-sweep finance audit → diagnostic mode
```

## Failure modes and responses

| Failure | Detection | Automated response | Operator action |
|---|---|---|---|
| Redis outage | `guardrail_degraded_total`, `provider_circuit_local_fallback_total` | Local token bucket + local circuit breaker | Restore Redis; watch per-pod limits |
| Finance invariant violation | `finance_audit_violation_total`, diagnostic alert | Diagnostic mode: sweeps halted, writes 503 | `POST /internal/diagnostic/clear` after repair |
| Ledger tampering | `ledger_chain_verification_failed_total` | CronJob fails, PagerDuty | Forensics on `ledger_events` |
| Reconciler partition | `ModelGovernorReconcilerNotLeader` | Standby pods idle | Check advisory lock holder |
| Provider storm | `provider_circuit_open_total` | Reserve blocked per provider | Failover / provider health |

## CronJob probes

| Job | Schedule | Purpose |
|---|---|---|
| `synthetic-canary` | */5 | Liveness: sidecar, gateway, reconciler |
| `governance-canary` | */10 | Diagnostic status + ledger verify-chain |
| `ledger-chain-verify` | hourly | Hash-chain integrity (422 on break) |
| `ledger-chain-anchor` | hourly :15 | Record verified head to `ledger_chain_anchors` |

## Enterprise overlay

Apply `deploy/overlays/enterprise` on Istio-enabled clusters for LLM egress allowlisting (`api.openai.com`, `api.anthropic.com`).

## Related

- `docs/slo-definitions.md` — 99.5% reserve availability, 500ms p95
- `docs/enterprise-hardening-roadmap.md` — OIDC, hash-chain, egress status
- `docs/operations-runbook.md` — operator playbooks
