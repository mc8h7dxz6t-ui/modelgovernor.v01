# Reliability and proof validation

This repository separates lightweight checks from higher-assurance proof runs.

## Tier 1: lightweight local checks (fast)

```bash
pytest -q tests/integration/test_ledger_hardening.py
pytest -q tests/integration/test_sidecar_admin_observability.py
pytest -q tests/load/test_load_harness.py
```

Purpose: quick regression checks on ledger logic, deterministic invariants, and internal-auth observability/admin read surfaces.

## Tier 2: Postgres-backed proof checks (real DB semantics)

Set `POSTGRES_TEST_URL` to a writable PostgreSQL instance, then run:

```bash
pytest -q tests/integration/test_postgres_reliability.py
```

These tests run against an isolated temporary database per test and apply the real SQL migrations (`migrations/0001`-`0004`) before execution.

Covered proof scenarios:
- contested trace-cap reservations on the same trace
- concurrent reconciler workers against the same expired rows
- provider request ID uniqueness conflict handling
- late-settlement behavior after stranded holds

## Tier 3: reproducible load/invariant report

Generate machine-readable output:

```bash
python scripts/generate_invariant_report.py --operations 120 --workers 12
```

Output:
- `artifacts/reliability/latest_invariant_report.json`

This report is intended for invariant validation (correctness) rather than throughput marketing claims.

## Honesty note

The load harness is intentionally scoped to deterministic control-plane correctness signals. It is not a substitute for full production benchmarking under representative infrastructure and provider traffic.
