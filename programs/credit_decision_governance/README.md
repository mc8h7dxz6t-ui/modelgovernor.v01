# Credit Decision Governance

Full program spec for **CreditGovern** — reserve-before-score credit decisions with spine audit trail.

## Flow

1. **Crystallize** — reserve exposure on approved model version
2. **Score** — mock inference rail (`mock_rail.py`)
3. **Commit** — settle approved exposure or release on REFER/BLOCKED

## Invariants

| Invariant | Enforcement |
|-----------|-------------|
| Model version allowlist | `credit_govern/main.py` |
| Reserve before score | Single crystallize per application |
| Exposure cap per policy | `credit-high-us` policy registry |
| Drift lockout on over-commit | Spine `exposure_drift.py` |

## Demo

```bash
make credit-demo
FG_SPINE_ENABLED=true make credit-demo
```

## Tests

```bash
pytest finance-governor/tests/test_credit_govern.py -q
pytest finance-governor/tests/programs/credit_decision_governance/ -q
```
