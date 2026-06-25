# Finance Governor

Institutional++ finance control plane — **own spine** (gateway / sidecar / reconciler) adapted from ModelGovernor, with **Crystal Commit Protocol** and optional standalone platforms.

## What this is

| Layer | Purpose |
|-------|---------|
| **Spine** | Shared governance: CCP, commit escrow, hash chain, regulatory_ops, horizon reconciler |
| **Platforms** | Standalone products (AlgoFreeze, WireMatch, …) that optionally plug into spine |

ModelGovernor and Finance Governor are **sibling spines** — same reliability patterns, different domains. They can run independently or co-exist in one org (AI spend vs financial commit control).

## Architecture

```
finance-governor/
├── spine/                 # Finance-adapted control plane (this is the spine)
│   ├── gateway/
│   ├── sidecar/
│   └── reconciler/
├── platforms/             # Standalone wedges + common adapter
│   ├── common/
│   ├── algofreeze/        # (Phase 1)
│   └── ...
├── migrations/
├── docker-compose.yml
└── docs → ../docs/finance-governor/
```

Full specification: [docs/finance-governor/spine.md](../docs/finance-governor/spine.md)

## Spine vs ModelGovernor spine

| ModelGovernor | Finance Governor spine |
|---------------|------------------------|
| `POST /reserve` (tokens) | `POST /crystallize` + optional exposure reserve |
| `POST /settle` (cost) | `POST /commit` (crystal-bound) |
| `user_wallets` | `account_ledgers` |
| `escrow_ledger` | `commit_escrow_ledger` |
| `trace_budget_state` | `exposure_budget_state` |
| `model_policy_registry` | `instrument_policy_registry` |
| `ledger_events` | `decision_events` + `governance_crystals` |
| `finance_ops` | `regulatory_ops` + `crystal_ops` |
| Provider dispatch | Platform action (algo/wire/credit) |

## Crystal Commit Protocol

Every irreversible action on the spine requires a **Governance Crystal**. See [crystal-commit-protocol.md](../docs/finance-governor/crystal-commit-protocol.md).

## Status

| Component | Status |
|-----------|--------|
| Spine schema (`migrations/0001`) | ✅ Design artifact |
| `platforms/common/crystal.py` | ✅ Protocol module |
| `platforms/common/spine_adapter.py` | ✅ Adapter contract |
| Spine services (gateway/sidecar/reconciler) | ✅ Phase 2 |
| Integration tests (23 passing) | ✅ |
| Decision hash chain + verify API | ✅ |
| Gateway auth on `/governed/commit` | ✅ |
| Diagnostic mode + reconciler sweep halt | ✅ |
| `make fg-certification` | ✅ |
| AlgoFreeze (Phase 1) | ✅ |
| WireMatch (Phase 1b) | ✅ |
| `make crystal-demo` walkthrough | ✅ |

```bash
make fg-stack-up          # spine + WireMatch + AlgoFreeze (from repo root)
make fg-spine-test        # pytest (23 tests)
make fg-certification     # unit suite + optional live chain verify
make crystal-demo         # 3-minute CCP walkthrough (stack must be up)
make algofreeze-demo      # Knight-class freeze smoke
make wirematch-demo       # Citigroup-class amount anomaly smoke
```

## Environment

```bash
cp .env.example .env
# POSTGRES_DB=financegovernor
# FG_SIDECAR_URL=http://localhost:8091
# FG_SPINE_ENABLED=true
```
