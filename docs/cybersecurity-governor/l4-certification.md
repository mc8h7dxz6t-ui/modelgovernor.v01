# L4 Gold Certification (Cybersecurity Governor)

Cybersecurity Governor L4 Gold is the internal enterprise gate for production-grade runtime security enforcement deployments.

## Gate composition

| Layer | Artifact | Command |
|-------|----------|---------|
| Invariant report | `artifacts/certification/` | `make cg-certification` |
| SQLite + spine tests | `cybersecurity-governor/tests/` | `make cg-spine-test` |
| Postgres vigorous | Tier 2 CI | `POSTGRES_TEST_URL=... pytest test_postgres_vigorous.py` |
| Chaos harness | toxiproxy | `make cg-chaos-test` |
| Helm enterprise | `deploy/helm/cybersecuritygovernor/` | `make cg-helm-enterprise` |
| L4 CI aggregator | offline reliability suite | `make cg-certification-l4-ci` |
| Examiner evidence | JSON + SHA-256 | `make cg-examiner-evidence` |

## Full L4 gate (requires Docker stack)

```bash
make cg-certification-l4
```

## CI offline gate

```bash
make cg-certification-l4-ci
```

## Related

- [capability-matrix.md](capability-matrix.md)
- [security-enforcement-mesh.md](security-enforcement-mesh.md)
- [operations-runbook.md](operations-runbook.md)
- [soc2-evidence-pack.md](soc2-evidence-pack.md)
