# Reliability testing — Cybersecurity Governor

## Tier 1 — SQLite unit (< 2s)

```bash
cd cyber-governor && make cg-spine-test
```

Covers: TCP core, spine lifecycle, mesh block, diagnostic mode, horizon sweep, invariants, lineage, S3 anchor mock, security chain verify/anchor.

## Tier 2 — Postgres vigorous

```bash
docker compose -f docker-compose.test.yml up -d
export CG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5444/cg_test
make cg-postgres-test
```

Validates real Postgres semantics: migrations 0001–0003, crystallize/commit, chain verify, anchor head.

## Tier 3 — Live demo / smoke

```bash
make cg-stack-up
make cg-security-demo
make cg-spine-smoke
```

## Tier 4 — K8s manifest gate

```bash
make cg-deploy-dry-run
# or: kustomize build deploy/base/ | kubectl apply --dry-run=client -f -
```

## Invariant probes (zero error budget)

| Probe | Module | Trigger |
|-------|--------|---------|
| Negative principal balance | `security_ops` | Post-reconciler sweep |
| Action cap overrun | `security_ops` | Post-reconciler sweep |
| Commit without crystal | `threat_ops` | Post-reconciler sweep |
| Duplicate commit events | `threat_ops` | Post-reconciler sweep |
| High-risk silent expire | `threat_ops` | Post-reconciler sweep |

On violation: `enter_diagnostic_mode()` + `security_audit_violation_total` increment.
