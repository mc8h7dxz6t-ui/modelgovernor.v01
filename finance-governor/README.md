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
| Integration tests (28+ passing) | ✅ |
| OIDC/RBAC (FG-native) | ✅ |
| Decision chain verify + S3 anchor | ✅ |
| Admin audit log | ✅ |
| `make fg-demo-gold` | ✅ |
| `make fg-certification` (4-tier) | ✅ |
| Helm chart (`deploy/helm/finance-governor`) | ✅ |
| AlgoFreeze (Phase 1) | ✅ |
| WireMatch (Phase 1b) | ✅ |
| `make crystal-demo` walkthrough | ✅ |

```bash
make fg-demo-up            # spine + platforms
make fg-demo-gold          # 11-step institutional++ walkthrough
make fg-certification      # 4-tier: unit → postgres → load → chain verify
make fg-spine-test         # pytest (28 unit/chaos tests)
make crystal-demo          # quick CCP walkthrough
```

All tooling lives under `finance-governor/` — **no ModelGovernor runtime dependency**.

Production: [deploy/PRODUCTION.md](deploy/PRODUCTION.md) · `make fg-prod-setup` · `make fg-helm-install`

## Environment

```bash
cp .env.example .env
# POSTGRES_DB=financegovernor
# FG_SIDECAR_URL=http://localhost:8091
# FG_SPINE_ENABLED=true
```
