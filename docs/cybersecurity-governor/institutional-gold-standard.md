# Institutional++ Gold Standard — Cybersecurity Governor

## Certification levels

| Level | Status | Requirements |
|-------|--------|--------------|
| **L1 Platform** | Done | Standalone EgressGovern, SpineAdapter local mode |
| **L2 Institutional** | Done | Diagnostic mode, security_ops probes, CCP |
| **L3 Institutional++** | Done | Hash chain verify, anchor table, guardrails + fallback |
| **L4 Gold** | Done | 4-tier CI, Helm chart, load harness, Prometheus rules |
| **L5 Helm overlay** | Istio STRICT mTLS templates in Helm | Not live cluster attestation |
| **L5 Institutional Self-Check Certified** | `make plug` + optional live attestation | Not SOC2 — see [maturity-ladder.md](../../governor-spine-core/docs/maturity-ladder.md) |

## Competitive tech edges (vs GRC / SIEM / CNAPP)

| Edge | Implementation |
|------|----------------|
| **Runtime enforcement** | ThreatProxy + EgressGovern block **before** dispatch, not post-hoc SIEM |
| **Security Enforcement Mesh** | 7 `crystal_mesh_rules` — posture drift / threat block revokes commit authority |
| **Provable security trail** | Hash-chained `security_events` + `verify-chain` + S3 Object Lock anchors |
| **Zero-error-budget invariants** | `security_ops` 7-probe suite + per-platform invariant counters |
| **Fail-closed degradation** | Redis guardrails → local fallback; circuit breaker on Redis flapping |
| **Enterprise RBAC** | OIDC JWT + security-admin gates on anchor/diagnostic |
| **Production deploy kit** | Helm chart (PgBouncer, Redis Sentinel, OTEL, PDB/HPA) + ArgoCD app |
| **Synthetic canaries** | CronJobs probe `/readyz`, `/internal/security/verify-chain`, egress golden path |
| **SLO observability** | Prometheus recording rules for crystallize/commit availability + p95 latency |
| **Examiner evidence pack** | `make cg-examiner-evidence` → JSON + `pack_sha256` |

## L4 Gold checklist (implemented)

### Data plane
- [x] Append-only `security_events` with hash chain on all paths (including sweeps)
- [x] `security_ops.assert_security_ops_invariants()` — 7 probes
- [x] `GET /internal/security/verify-chain`
- [x] `POST /internal/security/anchor-head` + `security_chain_anchors` migration

### Enforcement mesh
- [x] 7 cross-platform mesh rules in `0004_cg_platforms_mesh.sql`
- [x] Behavioral tests in `test_security_mesh.py`

### Degradation
- [x] Redis guardrails + symmetric local fallback
- [x] Reconciler halts sweeps in diagnostic mode
- [x] Diagnostic write halt on crystallize/commit

### Security
- [x] OIDC JWT + RBAC with integration tests
- [x] Dependency circuit breaker on Redis flapping
- [x] Admin audit log on privileged actions
- [x] Security-admin gate on diagnostic clear and anchor

### Observability
- [x] `/metrics/prometheus` RED metrics
- [x] Prometheus P1 rules in `deploy/helm/cybersecuritygovernor/files/prometheus-rules.yaml`
- [x] Governance canary hits `/internal/security/verify-chain`

### Testing pyramid
- [x] Tier 1: `make cg-spine-test` (75+ tests)
- [x] Tier 2: `test_postgres_vigorous.py` (CI `cg-test-tier2`)
- [x] Tier 3: `tests/load/test_cg_load_harness.py` (CI `cg-test-tier3`)
- [x] Tier 4: Toxiproxy chaos (`docker-compose.chaos.yml`, CI `cg-test-tier4-chaos`)

### Deploy
- [x] `deploy/helm/cybersecuritygovernor/` — CG-native env vars (`CG_INTERNAL_TOKENS`, `SECURITY_ANCHOR_S3_*`)
- [x] `deploy/argocd/application-cybersecuritygovernor-production-helm.yaml`
- [x] `deploy/infra/aws/security-anchor-bucket.yaml` — Object Lock bucket
- [x] CI: `cg-test-tier1` through `cg-test-tier4-chaos`, `cg-validate-helm`, `cg-certification-l4`

## Certification commands

```bash
make cg-spine-test           # Tier 1
make cg-load-test            # Tier 3
make cg-certification        # Tier 1 + load + artifact report
make cg-certification-strict # + chaos + live verify-chain
make cg-chaos-test           # Tier 4 (requires chaos compose up)
make cg-examiner-evidence    # Examiner diligence JSON + pack_sha256
make cg-certification-l4-ci  # Offline L4 Gold gate (CI)
helm lint deploy/helm/cybersecuritygovernor
```

## Plug-and-play platform model

Any platform integrates via **manifest + GovernedPlatform SDK**:

1. Add `platforms/<name>/manifest.yaml` + `main.py`
2. Register in `platforms/registry.yaml`
3. Seed row in migration `0004_cg_platforms_mesh.sql`
4. Add Helm `platforms:` entry + Dockerfile

See [security-enforcement-mesh.md](security-enforcement-mesh.md) for mesh rule authoring.
