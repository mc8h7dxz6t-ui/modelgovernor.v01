# L4 Gold Certification (Insurance Governor)

Insurance Governor L4 Gold is the internal enterprise gate for production-grade claim governance deployments.

## Gate composition

| Layer | Artifact | Command |
|-------|----------|---------|
| Invariant report | `artifacts/certification/` | `make ig-certification` |
| SQLite + spine tests | `insurance-governor/tests/` | `make ig-spine-test` |
| Postgres vigorous | Tier 2 CI | `POSTGRES_TEST_URL=... pytest test_postgres_vigorous.py` |
| Chaos harness | toxiproxy | `make ig-chaos-test` |
| Helm enterprise | `deploy/helm/insurancegovernor/` | `make ig-helm-enterprise` |
| L4 CI aggregator | offline reliability suite | `make ig-certification-l4-ci` |
| Examiner evidence | JSON + SHA-256 | `make ig-examiner-evidence` |

## Full L4 gate (requires Docker stack)

```bash
make ig-certification-l4
```

This runs certification, Helm enterprise render/tests, and examiner evidence generation.

## CI offline gate

```bash
make ig-certification-l4-ci
```

Runs Helm enterprise tests, horizon sweeper, commit invariants, claim seal fail-closed, and platform registry fail-closed without live Docker.

## Related

- [capability-matrix.md](capability-matrix.md)
- [operations-runbook.md](operations-runbook.md)
- [soc2-evidence-pack.md](soc2-evidence-pack.md)
