# Finance Governor — Capability Matrix (institutional++)

Use in RFPs, model risk questionnaires, and regulatory diligence. Status reflects **target** at Phase 3 unless noted.

**Deep dives:** [desirability](desirability.md) · [institutional gold standard](institutional-gold-standard.md)

## Certification levels

| Level | Requirements |
|-------|--------------|
| **L1 Platform Ready** | Standalone demo + Tier 1–2 tests |
| **L2 Institutional** | + diagnostic mode, invariants, metrics |
| **L3 Institutional++** | + hash chain, SLO alerts, load tests |
| **L4 Gold** | + chaos harness, K8s HA, S3 anchor, OIDC |

| Capability | Status | Phase 1 Demo | Phase 3 Production |
|------------|--------|--------------|-------------------|
| Reserve-before-inference governance | 🎯 | `make fg-demo-gold` | Gateway + sidecar |
| Credit decision API | 🎯 | Mock rail | Live inference rails |
| ISO 4217 exposure ledger (`NUMERIC(24,12)`) | 🎯 | Auto | Postgres |
| Append-only decision events + idempotent lifecycle | 🎯 | Step 7 demo | Postgres |
| Per-desk atomic exposure caps | 🎯 | Auto | Sidecar |
| Exposure drift enforcement + account lockout | 🎯 | Demo step | Sidecar |
| Leader-elected reconciler (expiry/stranded) | 🎯 | Step 1 + 11 | 2+ replicas |
| High-risk never silent-expire | 🎯 | Policy test | Reconciler + policy |
| Redis guardrails + local fallback | 🎯 | Auto | Sidecar |
| Inference rail circuit breaker | 🎯 | Demo step | Sidecar |
| Diagnostic mode (no poison pill) | 📋 Phase 2 | — | Redis cluster flag |
| Hash-chained decision events | 📋 Phase 2 | Verify API | Migration |
| Hourly chain verification CronJob | 📋 Phase 3 | — | K8s CronJob |
| S3 Object Lock external anchor | 📋 Phase 3 | Documented | CloudFormation + ESO |
| Privileged admin audit log | 📋 Phase 2 | Demo step | Migration |
| Gateway OIDC termination | 📋 Phase 2 | Documented | Config flag |
| Sidecar OIDC + RBAC | 📋 Phase 2 | Documented | Config flag |
| Model ownership registry | 📋 Phase 2 | Internal API | Postgres |
| Bias cohort monitoring hooks | 📋 Phase 2 | Metrics only | Prometheus |
| Explainability artifact binding | 🎯 | Settlement metadata | Sidecar |
| Regulatory export API | 📋 Phase 3 | — | `/internal/regulatory/export` |
| ExternalSecrets | 📋 Phase 3 | — | Production overlay |
| Redis Sentinel HA | 📋 Phase 3 | — | Production overlay |
| PgBouncer connection pooling | 📋 Phase 3 | HA compose | K8s + Helm |
| Istio egress allowlist + STRICT mTLS | 📋 Phase 3 | — | Enterprise overlay |
| Prometheus SLOs + burn-rate alerts | 📋 Phase 2 | `/metrics/prometheus` | PrometheusRule |
| Governance canary CronJobs | 📋 Phase 3 | — | K8s |
| GitOps (ArgoCD + Helm) | 📋 Phase 3 | Manifests | `deploy/argocd` |
| 4-tier CI (unit → Postgres → load → chaos) | ✅ unit + Postgres + Helm in CI | `make fg-spine-test` | GitHub Actions `finance-governor-test` |

Legend: 🎯 Phase 1 target | 📋 Planned phase

---

## Governance pillar coverage

| Pillar | Key capabilities |
|--------|------------------|
| **Regulatory Compliance** | Instrument policy registry, jurisdiction gates, regulatory export, EU AI Act risk tier |
| **Risk Management** | Exposure caps, drift lockout, bias hooks, stranded semantics, circuit breaker |
| **Accountability** | Multi-dimensional attribution, approval gates, ownership registry, SoD roles |
| **Monitoring** | Invariant counters, SLOs, synthetic probes, OTel spans |
| **Transparency** | Hash chain, verify API, explanation binding, external anchor, lineage |

---

## Pre-revenue valuation framing

Finance Governor inherits ModelGovernor's **proven institutional++ engineering** and applies it to **larger TAM** (all of regulated finance vs LLM spend only).

| Asset | Pre-revenue worth driver |
|-------|--------------------------|
| ModelGovernor spine (ported) | $900K–$1.6M replacement cost (proven) |
| Five platform specs + domain schema | $400K–$800K |
| Demo-ready standalone paths (when built) | $300K–$600K each at maturity |
| **Finance Governor bundle (design + spine IP)** | **$5M–$10M** fair value at full scaffold |

See [desirability.md](desirability.md) for buyer ROI and bundle ACV targets.

## Competitive positioning

| vs. | Finance Governor edge |
|-----|----------------------|
| **Model risk platforms (ValidMind, ModelOp)** | Runtime enforcement, not just validation lifecycle |
| **MLOps (MLflow, W&B)** | Institutional ledger + reconciler, not experiment logs |
| **Feature stores** | Pre-inference exposure control, not just serving |
| **Cloud AI guardrails** | Finance-specific policy, examiner-grade audit chain |
| **GRC suites** | Sub-second reserve-before-decision at inference boundary |
| **Homegrown wrappers** | 4-tier test pyramid + chaos harness + HA reconciler |

---

## Regulatory evidence mapping

| Examiner question | Proof artifact |
|-------------------|----------------|
| How do you prevent unapproved models in production? | `instrument_policy_registry` + version mismatch guardrail |
| Show me the audit trail for application X | `GET /internal/decision/{key}` + `decision_events` |
| How do you handle inference timeouts? | `STRANDED` semantics + reconciler events |
| Prove the log wasn't tampered with | `GET /internal/decisions/verify-chain` + S3 anchor |
| Who approved overrides above threshold? | `guardrail_incidents` + `admin_audit_log` |
| How do you monitor bias? | Cohort counters + `BIAS_ALERT` events |

---

## Proof commands (target)

```bash
make fg-demo-gold              # live ~5-min walkthrough
make fg-demo-gold-reliability  # invariants + reconciler drill
pytest tests/integration/      # fast suite
pytest tests/chaos/            # Toxiproxy regulatory ops
```

---

## Pre-revenue valuation framing

Finance Governor inherits ModelGovernor's institutional++ engineering proof (ledger, reconciler, hash chain, 4-tier CI) applied to a **larger TAM** (regulated finance vs LLM spend control). Wedge clarity (credit decision governance) de-risks go-to-market vs generic "AI for finance."

Comparable positioning: RegTech infrastructure layer — sold to CRO / Model Risk / CTO with compliance as champion.
