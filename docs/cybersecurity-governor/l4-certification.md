# L4 Gold Certification (Cybersecurity Governor)

**L4 Gold = institutional test + deploy kit gate** — not a claim that this repo is a Fortune 500 cyber product.

What L4 proves:

| Proven | Not proven |
|--------|------------|
| Pytest suite passes (spine, mesh, platforms) | Inline network enforcement without integration wiring |
| Helm enterprise manifests render | Okta/Zscaler-class identity or DLP replacement |
| Hash chain verify API works in tests | Customer VPC production attestation without `cg-stack-up` |
| Envoy ext_authz adapter denies off-allowlist hosts | Full CNAPP/SIEM dataplane |

## Gate composition

| Layer | Artifact | Command |
|-------|----------|---------|
| Invariant report | `artifacts/reliability/cybersecurity-governor/` | `make cg-certification` |
| Artifact presence | deploy kit files exist | `test_l4_artifacts_present.py` |
| Runtime enforcement | mesh + ext_authz + verify-chain | `test_l4_runtime_enforcement.py` |
| SQLite + spine tests | `cybersecurity-governor/tests/` | `make cg-spine-test` |
| Postgres vigorous | Tier 2 CI | `POSTGRES_TEST_URL=... pytest test_postgres_vigorous.py` |
| Chaos harness | toxiproxy | `make cg-chaos-test` |
| Helm enterprise | `deploy/helm/cybersecuritygovernor/` | `make cg-helm-enterprise` |
| L4 CI aggregator | offline reliability suite | `make cg-certification-l4-ci` |
| Examiner evidence | JSON + SHA-256 | `make cg-examiner-evidence` |

## Defensible wedge demo

```bash
make cg-stack-up
make cg-egress-wedge-demo   # Envoy ext_authz + identity arm + chain verify
```

Wire Envoy `ext_authz` HTTP filter to `http://egress-govern:8123/envoy/authz/check`.

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
