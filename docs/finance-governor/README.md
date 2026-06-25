# Finance Governor — Platform Vision

**Finance Governor** adapts the ModelGovernor institutional++ control-plane spine for financial services — plus **specialized platforms** that each solve a costly finance problem and can run **alone or plugged into the spine**.

ModelGovernor governs **LLM spend** (tokens, models, provider dispatch). Finance Governor governs **financial decisions and operations** — credit AI, algo freeze, wire matching, intercompany reconciliation, asset depreciation — with the same reliability primitives: Postgres as sole source of truth, append-only audit, reconciler repair, hash-chained evidence, and diagnostic mode under invariant violation.

## Platform model

Each platform is a **clean, deployable codebase** — not a feature flag in a monolith:

| Platform | Problem prevented | Standalone? |
|----------|-------------------|-------------|
| [AlgoFreeze](../../programs/algofreeze/) | Runaway algo / bad deploy ($440M-class) | ✅ |
| [WireMatch](../../programs/wire_match/) | Wrong wire / decimal error ($900M-class) | ✅ |
| [SubledgerSync](../../programs/subledger_sync/) | Intercompany drift at audit | ✅ |
| [AssetLedger](../../programs/asset_depreciation/) | Stale depreciation, wrong books | ✅ |
| [CreditGovern](../../programs/finance_governor/) | Ungoverned credit AI | ✅ |

**Optional spine** (gateway + ledger sidecar + reconciler) unifies audit, cross-platform invariants, and examiner export when you run multiple platforms.

See [platform-model.md](platform-model.md) and [code-driven-fixes.md](code-driven-fixes.md).

## Why this exists

Financial institutions lose millions annually to preventable failures — human data-entry errors, unoptimized algo execution, version-control gaps, wire mismatches, and reconciliation lag. Incumbent tools are post-hoc dashboards or monolithic ERP modules, not pre-execution control planes.

| Gap | Incumbent tooling | Finance Governor edge |
|-----|-------------------|----------------------|
| Pre-decision enforcement | Post-hoc monitoring | Reserve/freeze/gate **before** irreversible action |
| Audit trail | Scattered logs / spreadsheets | Append-only events + optional hash chain |
| Version integrity | Informal deploy process | Approved-version registry with auto-freeze |
| Ambiguous outcomes | Manual exception queues | Reconciler with `STRANDED` semantics |
| Deploy flexibility | All-or-nothing suites | Each platform functions alone or on spine |

## Document map

| Document | Purpose |
|----------|---------|
| [desirability.md](desirability.md) | **Why buyers want it** — ROI, personas, GTM, bundle ACV |
| [institutional-gold-standard.md](institutional-gold-standard.md) | **Industry++ reliability** — SLOs, invariants, testing, regulatory mapping |
| [platform-model.md](platform-model.md) | Standalone vs spine-connected deployment |
| [code-driven-fixes.md](code-driven-fixes.md) | Four deep-dive problems + code fixes |
| [market-gaps.md](market-gaps.md) | Underserved finance domains and wedge products |
| [governance-framework.md](governance-framework.md) | AI governance pillars → financial services mapping |
| [architecture.md](architecture.md) | Spine + platform architecture |
| [domain-model.md](domain-model.md) | Tables, state machines, invariants |
| [roadmap.md](roadmap.md) | Phased build plan and success criteria |
| [capability-matrix.md](capability-matrix.md) | Institutional++ checklist for RFPs |
| [spine-port-map.md](spine-port-map.md) | ModelGovernor → Finance Governor file ports |
| [quality-bar.md](quality-bar.md) | Merge gate and platform checklist |

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

The spine (optional) preserves the three-service split:

1. **Gateway** — OIDC auth, protocol normalization, orchestrate reserve → action → settle
2. **Ledger sidecar** — all state mutations in Postgres transactions
3. **Reconciler** — sweeps expired holds, strands ambiguous outcomes, runs invariant audit

## Build priority

1. **AlgoFreeze** — highest $/minute risk; Knight Capital narrative
2. **WireMatch** — universal treasury pain; NLP + type-safety
3. **SubledgerSync** — group CFO / multi-entity
4. **AssetLedger** — steady regulatory value
5. **CreditGovern** — AI credit wedge (regulatory-heavy)

## Quick start (when scaffold lands)

```bash
# Standalone — one platform, no spine
make algofreeze-demo
make wirematch-demo

# Spine + all platforms
make fg-spine-up
make fg-all-platforms-demo
```
