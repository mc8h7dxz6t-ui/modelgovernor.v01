# Finance Governor — Platform Vision

**Finance Governor** adapts the ModelGovernor institutional++ control-plane spine for financial services: a ledger-backed, reserve-before-action governance layer for AI systems operating in regulated finance contexts.

ModelGovernor governs **LLM spend** (tokens, models, provider dispatch). Finance Governor governs **financial AI decisions** (credit, fraud, pricing, compliance screening, portfolio signals) with the same reliability primitives: Postgres as sole source of truth, append-only audit, reconciler repair, hash-chained evidence, and diagnostic mode under invariant violation.

## Why this exists

Financial institutions deploy AI at scale but lack infrastructure that treats AI decisions with the same rigor as payments or trading:

| Gap | Incumbent tooling | Finance Governor edge |
|-----|-------------------|----------------------|
| Pre-decision enforcement | Post-hoc model monitoring dashboards | Reserve-before-dispatch: block high-risk inference before capital or customer impact |
| Audit trail | Scattered MLflow / vendor logs | Hash-chained, append-only decision ledger with external anchoring |
| Accountability | Model cards, informal ownership | Multi-dimensional attribution (desk, book, model version, approver) |
| Ambiguous outcomes | Manual exception queues | Reconciler with `STRANDED` semantics for timeout/dispute states |
| Regulatory evidence | Ad-hoc exports for examiners | Structured compliance artifacts mapped to EU AI Act / FCA / SR 11-7 |

## Document map

| Document | Purpose |
|----------|---------|
| [market-gaps.md](market-gaps.md) | Underserved finance domains and wedge products |
| [governance-framework.md](governance-framework.md) | AI governance pillars → financial services mapping |
| [architecture.md](architecture.md) | Spine adaptation: gateway / ledger / reconciler for finance |
| [domain-model.md](domain-model.md) | Tables, state machines, invariants |
| [roadmap.md](roadmap.md) | Phased build plan and success criteria |
| [capability-matrix.md](capability-matrix.md) | Institutional++ checklist for RFPs |

## Relationship to ModelGovernor

Finance Governor **copies the spine**, not the domain:

```
ModelGovernor                    Finance Governor
─────────────────────────────────────────────────────────
user_wallets                  →  account_ledgers (nostro/vostro/sub-ledger)
model_policy_registry         →  instrument_policy_registry
escrow_ledger                 →  decision_escrow_ledger
trace_budget_state            →  exposure_budget_state (desk/book/tenant)
provider_dispatch_attempts    →  inference_rail_attempts
ledger_events + hash chain    →  decision_events + hash chain (same pattern)
finance_ops invariants        →  regulatory_ops invariants
reconciler sweeper            →  exception reconciler (timeouts, disputes)
```

The three-service split is preserved:

1. **Gateway** — OIDC auth, protocol normalization, orchestrate reserve → inference → settle
2. **Ledger sidecar** — all decision-state mutations in Postgres transactions
3. **Reconciler** — sweeps expired holds, strands ambiguous outcomes, runs regulatory invariant audit

## First wedge: AI Credit Decision Governance

See `programs/finance_governor/` for the inaugural program: governed credit inference with exposure caps, bias monitoring hooks, explainability capture, and examiner-ready audit exports.

## Quick start (when scaffold lands)

```bash
# Phase 0 — design review (current)
cat docs/finance-governor/architecture.md

# Phase 1 — local demo (planned)
make fg-demo-up
make fg-demo-gold
```
