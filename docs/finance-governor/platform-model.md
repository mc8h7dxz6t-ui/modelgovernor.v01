# Platform Model — Standalone or Spine-Connected

Finance Governor is not one monolith. It is a **shared spine** plus **specialized platforms**, each solving a costly finance problem with a clean, focused codebase. Every platform must function **alone** or **plugged into the spine**.

## Design principle

```
┌─────────────────────────────────────────────────────────────────┐
│                     OPTIONAL: Finance Governor Spine             │
│  Gateway │ Ledger Sidecar │ Reconciler │ Hash Chain │ RBAC     │
└───────────────────────────────┬─────────────────────────────────┘
                                │ spine API (optional)
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   AlgoFreeze   WireMatch  SubledgerSync AssetLedger CreditGovern
   (standalone)  (standalone) (standalone) (standalone) (standalone)
```

**Standalone:** Platform ships as 1–2 services + Postgres (or SQLite for dev). No spine required. Full value on day one.

**Spine-connected:** Platform emits events to shared `decision_events` / `ledger_events`, inherits hash-chain audit, cross-platform invariants, unified RBAC, and examiner export. Enables multi-platform diligence from one control plane.

---

## Deployment modes

| Mode | When to use | What's included |
|------|-------------|-----------------|
| **Platform-only** | Single problem, fast pilot, edge deploy | Platform service(s) + platform schema |
| **Spine-lite** | Need audit chain, no full gateway | Sidecar read/write APIs + platform |
| **Full spine** | Enterprise, multi-platform, regulatory exam | Gateway + sidecar + reconciler + 1+ platforms |

### Platform-only compose

```yaml
# docker-compose.algofreeze.yml — no spine services
services:
  algofreeze-proxy:
    image: financegovernor/algofreeze:latest
  postgres:
    image: postgres:16
```

### Spine-connected compose

```yaml
# docker-compose.full.yml
services:
  fg-gateway:
  fg-sidecar:
  fg-reconciler:
  algofreeze-proxy:
    environment:
      FG_SPINE_ENABLED: "true"
      FG_SIDECAR_URL: http://fg-sidecar:8081
```

---

## Spine integration contract

Platforms that opt into the spine implement a thin **spine adapter** (~100 lines):

```python
# platforms/common/spine_adapter.py (conceptual)

class SpineAdapter:
    def reserve(self, operation: SpineOperation) -> ReserveResult: ...
    def settle(self, operation_id: str, outcome: SettlementOutcome) -> None: ...
    def emit_event(self, event_type: str, metadata: dict) -> None: ...
    def strand(self, operation_id: str, reason: str) -> None: ...
```

| Spine call | Platform use |
|------------|--------------|
| `reserve` | Hold budget / exposure / notional before irreversible action |
| `settle` | Record terminal outcome with artifact hash |
| `strand` | Ambiguous state — manual review required |
| `emit_event` | Non-financial audit (version check, feed drop, match score) |

**Standalone fallback:** When `FG_SPINE_ENABLED=false`, adapter writes to platform-local `platform_events` table with same schema shape. No functionality loss — only unified cross-platform view.

---

## Platform catalog

| Platform | Problem | Standalone value | Spine bonus |
|----------|---------|------------------|-------------|
| [AlgoFreeze](../../programs/algofreeze/) | Runaway algo / bad deploy | Heartbeat proxy + version freeze | Cross-desk kill switch audit |
| [WireMatch](../../programs/wire_match/) | Wrong wire / decimal error | NLP semantic gate before send | Payment + compliance unified trail |
| [SubledgerSync](../../programs/subledger_sync/) | Intercompany drift | FX-hash reconciliation pipeline | Group-wide invariant audit |
| [AssetLedger](../../programs/asset_depreciation/) | Stale depreciation | Cron-driven write-down engine | Regulatory table change audit chain |
| [CreditGovern](../../programs/finance_governor/) | Ungoverned credit AI | Reserve-before-score | Full regulatory export pack |

---

## Shared primitives (copy from ModelGovernor)

Platforms reuse these patterns without requiring the full spine:

| Primitive | Standalone use | Source |
|-----------|----------------|--------|
| Append-only events | Local audit table | `ledger_events` pattern |
| Idempotency key | Safe retries on wire/algo/reconcile | `ledger.py` |
| Circuit breaker | Feed drop → freeze | `circuit_breaker.py` |
| Diagnostic mode | Halt writes, keep reads | `diagnostic_mode.py` |
| Invariant probes | Post-batch SQL checks | `finance_ops.py` |
| Hash chain (optional) | Tamper evidence | `ledger_seal.py` |

---

## Cross-platform invariants (spine-connected only)

When multiple platforms share the spine, `regulatory_ops` can enforce group-level rules:

| Invariant | Platforms involved |
|-----------|-------------------|
| No outbound wire while algo desk is in FREEZE | WireMatch + AlgoFreeze |
| Intercompany entry must match settled wire reference | SubledgerSync + WireMatch |
| Asset write-down cannot exceed book value on linked ledger | AssetLedger + SubledgerSync |
| Credit auto-approve blocked during diagnostic mode | CreditGovern + spine |

---

## Repository layout

```
finance-governor/
├── spine/                    # Optional shared control plane
│   ├── gateway/
│   ├── sidecar/
│   └── reconciler/
├── platforms/
│   ├── common/               # spine_adapter, events, money
│   ├── algofreeze/
│   ├── wire_match/
│   ├── subledger_sync/
│   ├── asset_depreciation/
│   └── credit_govern/
├── programs/                 # Test + demo bundles per platform
└── docs/finance-governor/
```

Each `platforms/<name>/` directory is a **deployable unit** with its own:
- `Dockerfile`
- `docker-compose.standalone.yml`
- `README.md`
- `migrations/`
- `tests/`

---

## Buyer messaging

| Audience | Pitch |
|----------|-------|
| **Trading desk** | "Deploy AlgoFreeze standalone this week. Add spine when you want firm-wide audit." |
| **Treasury** | "WireMatch stops the $900M wire class of errors. No other platform required." |
| **Group CFO** | "Run all four platforms on shared spine — one examiner export, one invariant suite." |
| **RegTech** | "Same institutional++ patterns as ModelGovernor, per-finance-domain codebases." |

---

## Anti-patterns (avoid)

- ❌ Requiring spine for platform to function
- ❌ Monolithic binary with feature flags for all domains
- ❌ Shared mutable state between platforms (only spine events)
- ❌ Platform-specific logic in spine sidecar (spine is domain-agnostic)
