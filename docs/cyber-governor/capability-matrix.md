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
| OIDC RBAC (privileged paths) | 📋 Phase 3 |
| PgBouncer + Redis Sentinel HA | 📋 Phase 3 |
| Helm chart + ArgoCD | 📋 Phase 3 |
| Toxiproxy chaos harness | 📋 Phase 3 |

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
