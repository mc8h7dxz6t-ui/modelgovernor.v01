# AI Finance Ops Finals for LLMs

Institutional++ settlement, reconciliation, and finance-plane invariant program.

## Scope

- Reserve → dispatch → settle finalization
- Drift enforcement and wallet lockout
- Reconciler expiry, stranded holds, late settlement
- Session-wide finance invariant audit (`sidecar/app/finance_ops.py`)

## Tests

```bash
pytest -q tests/programs/finance_ops_finals/
```

## Key invariants

| Invariant | Enforcement |
|---|---|
| No negative wallet balances | Runtime probe + `assert_finance_ops_invariants` |
| No trace cap overrun | Atomic UPDATE + DB CHECK (Postgres) |
| No duplicate refunds/settlements | Event probes + unique indexes (Postgres) |
| Stranded holds have audit events | Finance ops audit query |
