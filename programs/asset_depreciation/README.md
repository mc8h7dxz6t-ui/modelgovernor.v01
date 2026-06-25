# AssetLedger — Smart Asset Depreciation Engine

**Standalone platform** for programmatic, regulation-driven asset write-downs — daily cron, not year-end manual batch.

## Problem

Thousands of assets with complex depreciation; manual updates lag. Overstated book values → tax overpayment, regulatory misstatement, bad quarterly reporting.

## Solution

Programmatic asset ledger with regulatory table sync:

- **Asset registry** — book value, method, jurisdiction
- **Reg table sync** — HMRC, IRS tables with version + effective date
- **Depreciation engine** — straight-line, declining-balance per policy
- **Cron scheduler** — daily run, append-only depreciation events

## Deployment modes

| Mode | Command (target) | Dependencies |
|------|------------------|--------------|
| Standalone | `make assetledger-demo` | Engine + Postgres + cron |
| Spine-connected | `FG_SPINE_ENABLED=true` | + sidecar settle with table version audit |

## Standalone architecture

```
HMRC / IRS tables ──► reg_table_sync
                              │
Asset registry ──► depreciation_engine ──► depreciation_events
                        │
                   cron scheduler (daily)
```

## Spine integration (optional)

- Each write-down `settle` with `reg_table_version` in metadata
- Examiner export: which regulatory table drove which charge
- SubledgerSync link: asset entity ↔ GL subledger balance check

## Core invariants

| Invariant | Enforcement |
|-----------|-------------|
| Book value never negative | Engine clamp + DB CHECK |
| Depreciation uses pinned table version | `reg_table_sync.py` |
| Events append-only | Postgres pattern |
| One charge per asset per period | Unique index (asset_id, period) |

## Module map

| File | Purpose |
|------|---------|
| `asset_registry.py` | Asset master |
| `reg_table_sync.py` | Regulatory rate tables |
| `depreciation_engine.py` | Period charge computation |
| `posting_emitter.py` | Event emission + optional GL bridge |

## Tests (target)

```bash
pytest -q tests/programs/asset_depreciation/
# test_daily_depreciation_run.py
# test_book_value_never_negative.py
# test_reg_table_version_pinned.py
# test_standalone_without_spine.py
```

## ModelGovernor ports

- `money.py` → Decimal precision for charges
- `ledger_events` pattern → `depreciation_events`
- CronJob K8s pattern from `synthetic-probe-cronjob.yaml`
