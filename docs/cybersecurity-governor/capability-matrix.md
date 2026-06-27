# Cybersecurity Governor — Capability Matrix (institutional++)

Status reflects **implemented** state on the L4 Gold track.

**Deep dives:** [institutional gold standard](institutional-gold-standard.md) · [security enforcement mesh](security-enforcement-mesh.md) · [operations runbook](operations-runbook.md)

## Certification levels

| Level | Requirements | Verify |
|-------|--------------|--------|
| **L1 Platform** | Standalone EgressGovern + spine adapter | `make cg-spine-test` |
| **L2 Institutional** | + diagnostic mode, `security_ops` probes | Tier 1 pytest |
| **L3 Institutional++** | + hash chain verify, anchor, guardrails | `GET /internal/security/verify-chain` |
| **L4 Gold** | + 4-tier CI, Helm HA, load harness, chaos | `make cg-certification-l4-ci` |
| **L5 Enterprise** | + Istio mTLS, zero-trust platform ingress | `test_l4_helm_enterprise.py` |

---

## Capability matrix

| Capability | Status | Demo / test | Production |
|------------|--------|-------------|------------|
| **Security Enforcement Mesh** (7 rules) | ✅ | `test_security_mesh.py` | `crystal_mesh_rules` |
| **EgressGovern** runtime allowlist commit gate | ✅ | `test_cyber_platforms.py` | Port 8123 |
| **ThreatProxy** pre-dispatch threat score gate | ✅ | `test_cyber_platforms.py` | Port 8125 |
| **PostureReconcile** CVE/patch drift → mesh blocks | ✅ | `test_security_mesh.py` | Port 8127 |
| **IdentityGovern** workload principal binding | ✅ | `test_cyber_platforms.py` | Port 8124 |
| **IncidentResponseGate** playbook authorization | ✅ | `test_cyber_platforms.py` | Port 8126 |
| **ComplianceLogger** SOC2/NIST evidence sealing | ✅ | `test_regulatory_export.py` | Port 8128 |
| Append-only `security_events` + hash chain | ✅ | `verify-chain` API | Postgres |
| S3 Object Lock external anchor | ✅ | `test_security_anchor.py` | Helm CronJob |
| OIDC JWT RBAC | ✅ | `test_auth_oidc.py` | Gateway + sidecar |
| Platform registry plug-and-play | ✅ | `test_platform_sdk.py` | Migration `0004` |
| Helm HA kit (PgBouncer, Sentinel) | ✅ | `helm lint` CI | `deploy/helm/cybersecuritygovernor` |
| Istio STRICT mTLS + platform→sidecar ingress | ✅ | `test_l4_helm_enterprise.py` | Enterprise overlay |
| SIEM export cache | ✅ | `0005_cg_production_state.sql` | `siem_export_cache` |

---

## Competitive positioning (real tech edge)

| vs. | Cybersecurity Governor edge |
|-----|----------------------------|
| **SIEM (Splunk, Sentinel)** | **Blocks commit at dispatch**, not post-hoc correlation |
| **GRC (ServiceNow, Archer)** | Runtime mesh rules enforced in milliseconds at spine |
| **CNAPP (Wiz, Prisma)** | Posture drift **revokes commit authority** on egress/IR |
| **Service mesh (Istio alone)** | Domain semantics: threat score, identity facets, mesh blocks |
| **SOAR playbooks** | IR gate requires crystallized authorization before action |

Runtime enforcement happens **before** exfiltration paths execute — rivals typically detect after the fact.
