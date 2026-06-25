# WireMatch — Semantic Gate for Cross-Border Payments

**Standalone platform** preventing misrouted wires via NLP semantic matching and strict type-safety before payment execution.

## Problem

Citigroup (2020): ~$900M wired to Revlon lenders vs ~$7.8M intended. Legacy systems use unstructured text; decimal transposition and beneficiary mismatch are not caught pre-send.

## Solution

Execution gate before payment rail:

- **Schema validation** — ISO 20022 / normalized Pydantic models
- **Type-safety** — `Decimal` amounts, currency quantum, IBAN checksum
- **Semantic matcher** — beneficiary + reference vs golden record
- **Anomaly scorer** — amount order-of-magnitude, transposition detection
- **HELD / REJECTED** — no silent send on low confidence

## Deployment modes

| Mode | Command (target) | Dependencies |
|------|------------------|--------------|
| Standalone | `make wirematch-demo` | Gate service + Postgres |
| Spine-connected | `FG_SPINE_ENABLED=true` | + sidecar fund reserve/settle |

## Standalone architecture

```
Wire request ──► WireMatch Gate ──► Payment rail (SWIFT, API)
                      │
         wire_schema + semantic_matcher
         anomaly_scorer + execution_gate
                      │
                 platform_events
```

## Spine integration (optional)

- `reserve` funds before wire send
- `settle` on rail confirmation
- `HELD` → `STRANDED` until compliance adjudication
- Link to SubledgerSync via shared wire reference hash

## Core invariants

| Invariant | Enforcement |
|-----------|-------------|
| No float amounts | Pydantic + `Decimal` only |
| No send below semantic threshold | `execution_gate.py` |
| Golden record version pinned | Policy registry |
| Held wires never auto-expire (high value) | Reconciler strand rule |

## Module map

| File | Purpose |
|------|---------|
| `wire_schema.py` | Normalized wire models |
| `semantic_matcher.py` | Embedding + rules match |
| `anomaly_scorer.py` | Amount / reference anomalies |
| `execution_gate.py` | APPROVED / HELD / REJECTED |

## Tests (target)

```bash
pytest -q tests/programs/wire_match/
# test_decimal_type_safety.py
# test_beneficiary_mismatch_held.py
# test_amount_anomaly_held.py
# test_approved_wire_passes.py
# test_standalone_without_spine.py
```

## ModelGovernor ports

- `money.py` → currency quantum
- `policy.py` → wire policy registry
- `attribution.py` → desk/entity attribution on wire
