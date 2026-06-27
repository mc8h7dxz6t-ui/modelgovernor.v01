# Finance Governor — Capability Matrix (institutional++)

Use in RFPs, model risk questionnaires, and regulatory diligence. Status reflects **implemented** state as of FG-ECP v1 (industry-leading track).

**Deep dives:** [desirability](desirability.md) · [institutional gold standard](institutional-gold-standard.md) · [external certification](../../finance-governor/docs/external-certification.md)

## Certification levels

| Level | Requirements | Verify |
|-------|--------------|--------|
| **L1 Platform Ready** | Standalone demo + Tier 1–2 tests | `make fg-spine-test` |
| **L2 Institutional** | + diagnostic mode, invariants, metrics | `make fg-certification` tier 1–2 |
| **L3 Institutional++** | + hash chain, SLO alerts, Postgres, chaos, reconciler sweeps | `make fg-certification` |
| **L4 Gold** | + K8s HA, PgBouncer, Sentinel, GitOps, synthetic probes | `make fg-certification-l4` |
| **L5 Institutional Self-Check** | + live rails, RDS, Istio all workloads, FG-ECP full attestation | `make fg-certification-external-full` |

Legend: ✅ Implemented · 🔌 Deploy-time config · 📄 Documented operator step

---

## Capability matrix (current)

| Capability | Status | Demo / test | Production |
|------------|--------|-------------|------------|
| Reserve-before-inference (crystallize + exposure) | ✅ | `make fg-demo-gold` | Gateway + sidecar |
| Credit decision API | ✅ | Mock + live HTTP rail | `FG_CREDIT_RAIL_MODE=live` |
| Live inference rails (HTTP provider + circuit breaker) | ✅ | `test_inference_rail.py` + Helm `fg-credit-rail` | `inference_rail.py` + enterprise chart |
| ISO 4217 exposure ledger (`NUMERIC(24,12)`) | ✅ | Auto | Postgres |
| Append-only decision events + idempotent lifecycle | ✅ | Step 7 demo | Postgres |
| Per-desk atomic exposure caps | ✅ | Auto | Sidecar |
| Exposure drift enforcement + account lockout | ✅ | `test_exposure_drift.py` | Sidecar |
| Leader-elected reconciler (expiry/stranded) | ✅ | `test_horizon_sweeper.py` + demo step 11 | 2+ replicas + PDB |
| High-risk never silent-expire | ✅ | `test_horizon_sweeper.py` + `test_commit_invariants.py` | Reconciler + policy |
| Redis guardrails + local fallback | ✅ | Auto | Sidecar |
| Inference rail circuit breaker | ✅ | `rail_circuit_open_total` | CreditGovern + sidecar attempts |
| Diagnostic mode (no poison pill) | ✅ | `test_diagnostic_mode.py` | Redis / API flag |
| Hash-chained decision events | ✅ | `verify-chain` API | Migration + sidecar |
| Hourly chain verification CronJob | ✅ | Helm template | `decisionChainVerify` CronJob |
| S3 Object Lock external anchor | ✅ | `decisionChainAnchor` CronJob (validates `anchored:true`) | 🔌 `s3Anchor.bucket` + IAM — S3 path operator-verified |
| Privileged admin audit log | ✅ | Demo + `/internal/admin/audit` | Postgres |
| Gateway OIDC termination | ✅ | `test_auth_oidc.py` | `oidc.enabled: true` |
| Sidecar OIDC + RBAC | ✅ | `require_financial_admin` | Config + middleware |
| Instrument / model policy registry | ✅ | Seeded policies | `instrument_policy_registry` |
| Platform registry (plug-and-play) | ✅ | `test_platform_registry.py` | Migration `0004` |
| Facet schema validation | ✅ | `test_facet_schemas.py` | Crystallize gate |
| Bias cohort monitoring hooks | ✅ | Prometheus counters | `fg_platform_invariant_events_total` |
| Explainability artifact binding | ✅ | CreditGovern metadata | Commit facets + rail outcome |
| Regulatory export API | ✅ | `test_regulatory_export.py` | `/internal/regulatory/export` |
| ExternalSecrets | ✅ | Helm template | 🔌 `externalSecrets.enabled` |
| Redis Sentinel HA | ✅ | L4 enterprise render | `values-enterprise.yaml` |
| PgBouncer connection pooling | ✅ | L4 enterprise render | `templates/pgbouncer.yaml` |
| Managed Postgres (AWS RDS) | ✅ | `values-rds.yaml` | 🔌 `postgres.external.enabled` |
| Istio egress allowlist + STRICT mTLS | ✅ | `kustomize/overlays/enterprise` | Enterprise overlay |
| Istio sidecar injection (all workloads) | ✅ | L5 Helm annotations | `istio.enabled: true` |
| Prometheus SLOs + burn-rate alerts | ✅ | `/metrics/prometheus` | `PrometheusRule` |
| Governance + platform canary CronJobs | ✅ | Helm templates | K8s CronJob |
| Synthetic spine canary (gateway/sidecar/reconciler) | ✅ | `reliability-cronjobs.yaml` | `fg-synthetic-canary` |
| AlgoFreeze version + WireMatch golden probes | ✅ | Helm reliability cronjobs | K8s CronJob |
| PodDisruptionBudget (sidecar, gateway, reconciler, pgbouncer, platforms) | ✅ | `test_l4_extended_pdb_coverage` | `values-enterprise.yaml` |
| Reconciler / PgBouncer liveness probes | ✅ | L4 Helm enterprise gate | Enterprise chart |
| Examiner evidence pack (FG-ECP L5) | ✅ | `make fg-examiner-evidence` | Attestation JSON |
| GitOps (ArgoCD + Helm) | ✅ | `deploy/argocd/` | Application manifest |
| Platform SDK plug-and-play | ✅ | `make fg-platform-conformance` | `platform_sdk.py` |
| External vendor certification (FG-ECP) | ✅ | `make fg-certification-external-full` | Attestation JSON + SHA256 |
| 4-tier CI (unit → Postgres → load → chaos) + L4 gate | ✅ | `.github/workflows/fg-ci.yml` | GitHub Actions |
| CCP surprise-budget behavioral tests | ✅ | `test_commit_invariants.py` | Invariant counters |
| Offline load smoke (12 lifecycle ops) | ✅ | `test_load_smoke_offline.py` | CI Tier 3 |
| 120+ automated tests | ✅ | `pytest tests/` | CI |

---

## Governance pillar coverage

| Pillar | Key capabilities |
|--------|------------------|
| **Regulatory Compliance** | Instrument policy registry, jurisdiction gates, regulatory export, EU AI Act risk tier |
| **Risk Management** | Exposure caps, drift lockout, bias hooks, stranded semantics, circuit breaker |
| **Accountability** | Multi-dimensional attribution, approval gates, ownership registry, SoD roles |
| **Monitoring** | Invariant counters, SLOs, synthetic probes, PodMonitor |
| **Transparency** | Hash chain, verify API, explanation binding, external anchor, lineage |

---

## Competitive positioning

| vs. | Finance Governor edge |
|-----|----------------------|
| **Model risk platforms (ValidMind, ModelOp)** | Runtime enforcement, not just validation lifecycle |
| **MLOps (MLflow, W&B)** | Institutional ledger + reconciler, not experiment logs |
| **Feature stores** | Pre-inference exposure control, not just serving |
| **Cloud AI guardrails** | Finance-specific policy, examiner-grade audit chain |
| **GRC suites** | Sub-second reserve-before-decision at inference boundary |
| **Homegrown wrappers** | 100+ tests, chaos harness, FG-ECP vendor attestation |

---

## Regulatory evidence mapping

| Examiner question | Proof artifact |
|-------------------|----------------|
| How do you prevent unapproved models in production? | `instrument_policy_registry` + version mismatch guardrail |
| Show me the audit trail for application X | `GET /internal/crystals/{id}/reconstruct` + `decision_events` |
| How do you handle inference timeouts? | `STRANDED` semantics + reconciler + rail circuit breaker |
| Prove the log wasn't tampered with | `GET /internal/decisions/verify-chain` + S3 anchor |
| Who approved overrides above threshold? | `guardrail_incidents` + `admin_audit_log` |
| How do you monitor bias? | Cohort counters + `BIAS_ALERT` events |
| Third-party platform certified? | FG-ECP attestation report (`report_sha256`) |

---

## Proof commands

```bash
cd finance-governor
make fg-demo-gold                  # institutional++ walkthrough
make fg-certification-l4           # L4 Gold internal gate
make fg-platform-conformance       # plug-and-play SDK
make fg-certification-external     # L5 vendor attestation (FG-ECP)
pytest tests/ -q --ignore=tests/integration
```

---

## Pre-revenue valuation framing

Finance Governor inherits ModelGovernor's **proven institutional++ engineering** and applies it to **larger TAM** (all of regulated finance vs LLM spend only).

See [desirability.md](desirability.md) for buyer ROI and bundle ACV targets.
