# Cybersecurity Governor — Capability Matrix (institutional++)

Status reflects **implemented** state on the L4 Gold track.

**Honest pitch:** tamper-evident authorization ledger for security commits — crystallize → mesh → commit → prove.

**Deep dives:** [institutional gold standard](institutional-gold-standard.md) · [security enforcement mesh](security-enforcement-mesh.md) · [operations runbook](operations-runbook.md)

## Certification levels

| Level | Requirements | Verify |
|-------|--------------|--------|
| **L1 Platform** | Standalone EgressGovern + spine adapter | `make cg-spine-test` |
| **L2 Institutional** | + diagnostic mode, `security_ops` probes | Tier 1 pytest |
| **L3 Institutional++** | + hash chain verify, anchor, guardrails | `GET /internal/security/verify-chain` |
| **L4 Gold** | + artifact presence, runtime enforcement tests, Helm render | `make cg-certification-l4-ci` |
| **L5 Institutional Self-Check Certified** | `make plug` | Portfolio harness (CI-enforced) |
| **L5 Helm overlay (Istio templates)** | Istio STRICT mTLS manifest gate | `test_l4_helm_enterprise.py` — not live cluster attestation |

L4 Gold is an **institutional test + deploy kit gate** — not a production cyber suite certification.

---

## Capability matrix

| Capability | Status | Demo / test | Production wiring |
|------------|--------|-------------|-------------------|
| **Security Enforcement Mesh** | ✅ spine | `test_security_mesh.py`, `test_l4_runtime_enforcement.py` | `crystal_mesh_rules` |
| **EgressGovern** allowlist commit gate | ✅ | `test_cyber_platforms.py` | Port 8123; optional Envoy ext_authz |
| **Envoy ext_authz adapter** | ✅ | `test_l4_runtime_enforcement.py` | `/envoy/authz/check` |
| **IdentityGovern** session arm + verify | ✅ | `test_cyber_platforms.py` | Port 8124 |
| **ThreatProxy** pre-dispatch threat score | ✅ thin wedge | `test_cyber_platforms.py` | Port 8125 |
| **IncidentResponseGate** playbook auth | ✅ thin wedge | `test_cyber_platforms.py` | Port 8126 |
| **PostureReconcile** CVE/patch drift | ✅ | `test_security_mesh.py` | Port 8127 |
| **ComplianceLogger** evidence sealing | ✅ thin wedge | `test_regulatory_export.py` | Port 8128 |
| **WitnessBridge** critical event ingest | ✅ | `cg-security-demo` | Port 8129 |
| **LineageIngest** structural DAG ingest | ✅ | `cg-security-demo` | Port 8130 |
| **ContentGuard** pre-publish pattern gate | ✅ | `content-guard-demo` | Port 8131 |
| Append-only `security_events` + hash chain | ✅ | `verify-chain` API | Postgres |
| S3 Object Lock external anchor scaffold | ✅ | `test_security_anchor.py` | Helm CronJob |
| OIDC JWT RBAC | ✅ | `test_auth_oidc.py` | Gateway + sidecar |
| Platform registry plug-and-play | ✅ | `test_platform_sdk.py` | Migration `0004` |
| Helm HA kit (PgBouncer, Sentinel) | ✅ | `helm lint` CI | `deploy/helm/cybersecuritygovernor` |
| Istio STRICT mTLS + platform→sidecar ingress | ✅ | `test_l4_helm_enterprise.py` | Enterprise overlay |

---

## What we are not (yet)

| Category error | Reality |
|----------------|---------|
| Okta / IGA replacement | Session arm + mesh parent — integration wedge, not IdP |
| Zscaler DLP replacement | Allowlist gate + ext_authz hook — needs proxy wiring |
| Splunk / SIEM replacement | Witness ingest + chain seal — not correlation engine |
| Wiz / CNAPP replacement | Posture drift → mesh block — not cloud graph |

Runtime enforcement at **commit time** is the wedge; dataplane integration is buyer SOW.
