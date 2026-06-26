# Cybersecurity Governor — Capability Matrix (Institutional++)

Use in RFPs, SOC 2 questionnaires, and CISO diligence.

## Certification levels

| Level | Requirements |
|-------|--------------|
| **L1 Platform Ready** | Standalone demo + Tier 1 tests |
| **L2 Institutional** | + diagnostic mode, invariants, metrics |
| **L3 Institutional++** | + hash chain, SLO alerts, Postgres tests |
| **L4 Gold** | + K8s deploy kit, S3 witness anchor, governance canary |

| Capability | Status |
|------------|--------|
| Threat Crystal Protocol (TCP) | ✅ |
| Crystallize → commit lifecycle | ✅ |
| Append-only `security_events` + hash chain | ✅ |
| `GET /internal/security/verify-chain` | ✅ |
| `POST /internal/security/anchor-head` | ✅ |
| S3 Object Lock witness quorum | ✅ |
| Session Horizon strand (critical/high) | ✅ |
| Threat Mesh cross-platform blocks | ✅ |
| Diagnostic mode (writes halt, reads continue) | ✅ |
| `security_ops` + `threat_ops` invariant probes | ✅ |
| Reconciler leader + horizon sweep | ✅ |
| Lineage ingest (Falco/Tetragon/generic) | ✅ |
| Structural DAG `lineage_edges` | ✅ |
| Standalone platforms (`CG_SPINE_ENABLED=false`) | ✅ |
| K8s base manifests + CronJobs | ✅ |
| PrometheusRule alerts | ✅ |
| Strand egress NetworkPolicy template | ✅ |
| 4-tier CI (unit → Postgres → demo → K8s dry-run) | ✅ |
| Synthetic + governance canary CronJobs | ✅ |
| DB invariant CHECK constraints | ✅ |
| Toxiproxy chaos harness | ✅ |
| Hypothesis property tests (hash chain) | ✅ |
| PostureReconcile (CNAPP/K8s baseline gate) | ✅ |
| ContentGuard (pre-publish PII/secret gate) | ✅ |
| K8s staging/production overlays + ESO | ✅ |
| Auto-generated secrets (`cg-bootstrap`) | ✅ |
| OIDC RBAC (privileged paths) | ✅ sidecar + gateway |
| admin_audit_log (hash-chained) | ✅ |
| PgBouncer + Redis Sentinel HA | ✅ production overlay |
| Istio mTLS + egress allowlist | ✅ enterprise overlay |
| Istio AuthorizationPolicy (adapter → spine) | ✅ enterprise overlay |
| Helm chart + ArgoCD | 📋 Phase 4 roadmap |

Legend: ✅ shipped | 📋 planned

## Governance pillar coverage

| Pillar | Mechanisms |
|--------|------------|
| **Detect** | WitnessBridge, LineageIngest, invariant counters |
| **Respond** | STRAND semantics, Threat Mesh, diagnostic mode |
| **Recover** | Reconciler repair, forensic reconstruct API |
| **Prove** | Hash chain verify, S3 anchor, security_chain_anchors |

## Test commands

```bash
make cg-spine-test           # Tier 1 — 25+ unit tests
make cg-postgres-test        # Tier 2 — Postgres vigorous
make cg-security-demo        # Tier 3 — live multi-vector demo
make cg-deploy-dry-run       # Tier 4 — K8s manifest validation
make cg-proof-test           # All tiers (local)
```
