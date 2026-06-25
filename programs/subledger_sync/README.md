# SubledgerSync — Automated Intercompany Reconciliation

**Standalone platform** matching intercompany transactions in real time using FX snapshots and transaction hashing — not at year-end audit.

## Problem

Multi-entity groups (UK/US, subsidiaries) accumulate FX timing and rate-source discrepancies. Millions in audit fees and tax inefficiency from manual month-end reconciliation.

## Solution

Event-driven reconciliation pipeline:

- **FX snapshot** — rate + timestamp hash at match time (ECB, Refinitiv, etc.)
- **Transaction hasher** — canonical hash for cross-entity pairing
- **Match engine** — graph pairing with FX tolerance
- **Discrepancy reporter** — alert at transaction clear, not audit

## Deployment modes

| Mode | Command (target) | Dependencies |
|------|------------------|--------------|
| Standalone | `make subledger-demo` | Reconciler worker + Postgres |
| Spine-connected | `FG_SPINE_ENABLED=true` | + sidecar settle/strand for orphans |

## Standalone architecture

```
Entity A API ──► event bus ──► SubledgerSync ──► match results
Entity B API ──► event bus ──►       │
                              fx_snapshot + txn_hasher
                              match_engine + discrepancy_reporter
```

## Spine integration (optional)

- Matched pairs `settle` with `fx_hash` metadata
- Unmatched `STRANDED` after match window
- Group `regulatory_ops`: zero orphaned intercompany after sweep
- WireMatch reference hash links payment to IC entry

## Core invariants

| Invariant | Enforcement |
|-----------|-------------|
| FX rate snapshot on every match attempt | `fx_snapshot.py` |
| Mirrored amounts within tolerance | `match_engine.py` |
| Discrepancy emitted within N minutes of clear | Async pipeline SLA |
| No duplicate match of same txn hash | Unique index |

## Module map

| File | Purpose |
|------|---------|
| `fx_snapshot.py` | Rate fetch + hash |
| `txn_hasher.py` | Canonical transaction hash |
| `match_engine.py` | Pair finding + tolerance |
| `discrepancy_reporter.py` | Real-time alerts |

## Tests (target)

```bash
pytest -q tests/programs/subledger_sync/
# test_mirrored_pair_matched.py
# test_fx_drift_flagged.py
# test_orphan_stranded_on_spine.py
# test_standalone_without_spine.py
```

## ModelGovernor ports

- `reconciler/app/sweeper.py` → orphan sweep pattern
- `finance_ops.py` → intercompany balance probes
- `ledger_seal.py` → match event hash chain
