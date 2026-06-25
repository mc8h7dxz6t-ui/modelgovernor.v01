# Institutional++ Gold Standard — Reliability & Robustness

What **industry-leading, institutional++ grade** means for Finance Governor — not as marketing, but as **testable, operable, examiner-defensible** requirements inherited from ModelGovernor and extended for regulated finance.

## Definition

**Institutional++** = controls that satisfy **three audiences simultaneously**:

1. **Engineering** — correct under failure, provable invariants, chaos-tested
2. **Operations** — SLOs, runbooks, diagnostic mode (no poison pill)
3. **Risk / Compliance** — tamper-evident audit, regulatory mapping, segregation of duties

A platform is **not** institutional++ if it only has good ideas in docs. It must ship:

- Append-only financial/decision event trail
- Idempotent mutation paths
- Exact-decimal money handling
- Reconciler for ambiguous states
- Invariant probes with **zero error budget**
- 4-tier test pyramid including Postgres + chaos
- Production K8s manifests with HA patterns

ModelGovernor proves this bar for AI spend. Finance Governor applies the **same bar** per platform and on the optional spine.

---

## Industry standard mapping

How Finance Governor controls map to what regulators and enterprise procurement actually ask for.

### Regulatory & supervisory frameworks

| Standard | Requirement | Finance Governor mechanism |
|----------|-------------|---------------------------|
| **OCC SR 11-7 / Fed SR 11-7** | Model risk management, ongoing monitoring | CreditGovern: version lock, lineage, monitoring counters |
| **EU AI Act (high-risk)** | Art. 9–15: risk mgmt, logging, transparency | Policy registry, decision_events, explanation binding |
| **FCA DP5/23 / SS1/23** | Accountability, consumer outcomes | Attribution dimensions, guardrail incidents |
| **BCBS 239** | Risk data aggregation accuracy | SubledgerSync: match at source, FX hash |
| **BSA / AML** | Audit trail on screening disposition | WireMatch + CreditGovern strand semantics |
| **MiFID II / MAR** | Algo trading controls | AlgoFreeze: version + feed integrity |
| **SOX / internal controls** | Prevent material misstatement | AssetLedger + SubledgerSync invariants |
| **ECOA / Reg B** | Adverse action explainability | CreditGovern settlement metadata |

### Enterprise assurance frameworks

| Framework | Control area | Finance Governor evidence |
|-----------|--------------|---------------------------|
| **SOC 2 Type II** | Logical access, change mgmt | OIDC RBAC, admin_audit_log, version registry |
| **ISO 27001** | Cryptographic controls, logging | Hash chain, S3 Object Lock anchor |
| **NIST CSF** | Detect, respond | Prometheus alerts, diagnostic mode |
| **PCI DSS** (adjacent) | Prevent unauthorized transmission | WireMatch gate, AlgoFreeze egress block |

### Operational resilience (UK / EU)

| Requirement | Source | Implementation |
|-------------|--------|----------------|
| Impact tolerance | FCA/PRA operational resilience | SLOs + freeze semantics; no silent failure |
| Recovery time | Internal RTO/RPO | Diagnostic mode keeps reads alive; reconciler repair |
| Third-party risk | Vendor inference rails | inference_rail_attempts + circuit breaker |

---

## The institutional++ reliability stack

Inherited from ModelGovernor `docs/institutional-reliability.md` and `docs/quality-bar.md`:

```
                    ┌─────────────────────────────────────┐
  Ingress           │  Gateway / platform proxy           │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
  Control plane     │  Sidecar or platform core (3+ replicas) │
                    │  • Redis guardrails + local fallback   │
                    │  • Circuit breaker + local fallback  │
                    │  • Diagnostic write halt             │
                    │  • OIDC RBAC on privileged paths       │
                    └──────────────┬──────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
    PgBouncer                 Redis HA                 OTEL / Prometheus
         │                         │
         ▼                         │
    Postgres (SoT) ◄───────────────┘ diagnostic flag
         ▲
         │
    Reconciler (leader election)
    • sweep / strand / repair
    • post-sweep regulatory_ops audit
```

### Five non-negotiable design principles

1. **Postgres is authoritative** — Redis is never the ledger
2. **Fail closed on money/actions, fail open on reads** — diagnostic mode
3. **Symmetric degradation** — Redis down → local fallback, not unbounded bypass
4. **Tamper-evident audit** — hash chain + hourly verify + external anchor
5. **Single-writer reconciliation** — advisory lock; idempotent sweeps

---

## Per-platform gold standard requirements

Each standalone platform must meet **Platform Baseline**; spine-connected adds **Spine Extensions**.

### Surprise Budget = 0 (CCP invariant)

Financial safety invariants have **no error budget**. CCP adds:

| Signal | Meaning |
|--------|---------|
| `surprise_commit_blocked_total` | Commit attempted without valid crystal |
| `crystal_horizon_strand_total` | Ambiguity stranded, not guessed |
| `crystal_fingerprint_mismatch_total` | Facet drift blocked at commit |
| `crystal_mesh_block_total` | Cross-platform parent crystal blocked child |

Any increase → **P1 page** (same class as ModelGovernor `finance_ops` violations).

---

## Platform Baseline (all five)

| Control | Requirement | Verification |
|---------|-------------|--------------|
| **Pre-execution gate** | No irreversible action without policy check | Integration test |
| **Append-only events** | No UPDATE/DELETE on audit table | Schema + test |
| **Idempotency** | Safe retry on all mutations | Replay test |
| **Exact decimal** | `NUMERIC(24,12)` or currency quantum | Property test |
| **Typed APIs** | Pydantic v2 models, no raw dicts | Schema validation test |
| **Health endpoints** | `/healthz`, `/readyz` | K8s probe |
| **Structured metrics** | Prometheus counters per invariant | Scrape test |
| **Standalone boot** | Single Compose command | CI smoke |
| **Diagnostic mode** | Halt writes, keep reads on invariant breach | Integration test |
| **Runbook** | Failure mode documented | Doc review |

### Spine Extensions (optional)

| Control | Requirement |
|---------|-------------|
| Hash-chained events | `decision_seal.py` pattern |
| Chain verify API | `GET /internal/decisions/verify-chain` |
| Hourly CronJob | Chain verification |
| S3 Object Lock anchor | External immutability |
| Cross-platform invariants | `regulatory_ops` group probes |
| OIDC RBAC | SoD roles on privileged paths |
| 4-tier CI | unit → Postgres → load → chaos |

---

## Platform-specific invariants (zero error budget)

These mirror ModelGovernor's `finance_ops` — **any violation is critical, no SLO burn allowance**.

### AlgoFreeze

| Invariant | Probe |
|-----------|-------|
| Zero order egress when `FROZEN` | `frozen_egress_attempt_total` must stay 0 |
| Version mismatch triggers freeze within policy SLA | `version_mismatch_freeze_total` |
| Freeze events append-only | DB constraint + event probe |
| Feed gap detection within N ms | `feed_degraded_total` + latency histogram |

### WireMatch

| Invariant | Probe |
|-----------|-------|
| No wire send below semantic threshold | `wire_sent_below_threshold_total` = 0 |
| No float amounts in wire path | Static analysis + runtime type check |
| High-value HELD never auto-expires without adjudication | Reconciler strand probe |
| Duplicate send same idempotency_key | Unique index + event probe |

### SubledgerSync

| Invariant | Probe |
|-----------|-------|
| FX snapshot hash on every match attempt | Metadata probe |
| No duplicate match of same txn hash | Unique index |
| Orphan intercompany > 0 after sweep window | `ic_orphan_detected_total` |
| Matched pair amounts within tolerance | `match_tolerance_breach_total` = 0 |

### AssetLedger

| Invariant | Probe |
|-----------|-------|
| Book value never negative | DB CHECK + `negative_book_value_total` = 0 |
| One depreciation per asset per period | Unique (asset_id, period) |
| Charge uses pinned reg_table_version | Settlement metadata probe |
| Depreciation events append-only | Event probe |

### CreditGovern

| Invariant | Probe |
|-----------|-------|
| No negative exposure balance | `negative_balance_detected_total` = 0 |
| No exposure cap overrun | Atomic UPDATE + probe |
| High-risk never silent-expire | `high_risk_auto_expired_total` = 0 |
| Settlement identity match | `attribution_identity_mismatch_total` |
| No duplicate settlement | Event probe |

### Spine (cross-platform)

| Invariant | Probe |
|-----------|-------|
| No wire send while desk FROZEN | Cross-platform probe |
| Ledger chain integrity | Hourly verify CronJob |
| Single reconciler leader | `reconciler_leader` gauge |
| Diagnostic mode blocks writes only | Write 503, read 200 |

---

## SLO definitions (institutional++)

### Availability SLOs (error budget allowed)

| SLI | Target | Platform |
|-----|--------|----------|
| Gate/reserve success rate | **99.5%** / 30d | All platforms |
| Gate/reserve p95 latency | **≤ 500ms** | All platforms |
| Freeze activation p99 | **≤ 100ms** | AlgoFreeze |
| Wire gate decision p95 | **≤ 200ms** | WireMatch |
| Match pipeline lag p95 | **≤ 60s** from clear | SubledgerSync |

### Safety invariants (zero error budget)

Port ModelGovernor `docs/slo-definitions.md` pattern:

> Financial safety invariants have **no error budget**. Any increase triggers immediate critical response.

| Signal | Alert severity |
|--------|----------------|
| Any `*_detected_total` invariant counter > 0 | **P1 — page** |
| `regulatory_audit_violation_total` | **P1 — diagnostic mode** |
| `ledger_chain_verification_failed_total` | **P1 — forensics** |
| Reserve/gate availability < 99.5% | **P2 — burn rate** |

### Burn-rate alerts

| Alert | Condition |
|-------|-----------|
| Fast burn | >14.4× error budget consumption in 1h |
| Slow burn | >3× error budget consumption in 6h |

---

## 4-tier testing pyramid (gold standard)

Copied from ModelGovernor `docs/reliability-testing.md` — **mandatory for institutional++ certification**.

| Tier | Scope | Finance Governor requirement |
|------|-------|------------------------------|
| **1 — Unit** | Pure logic, fast SQLite | 80%+ on gate, matcher, engine modules |
| **2 — Postgres integration** | Real transactions, constraints | All invariant probes; property-based ledger tests |
| **3 — Load** | Concurrent reserve/gate/freeze | Correctness under load; no cap overrun |
| **4 — Chaos** | Toxiproxy network partition | Finance ops survive Redis/DB latency |

### Per-platform minimum test counts (target)

| Platform | Tier 2 tests | Tier 4 chaos |
|----------|--------------|--------------|
| AlgoFreeze | 15+ | Feed partition + freeze |
| WireMatch | 15+ | Gate under DB slow |
| SubledgerSync | 20+ | FX API timeout |
| AssetLedger | 12+ | Cron + DB failover |
| CreditGovern | 25+ | Full lifecycle chaos |
| Spine | 30+ | Cross-platform invariant |

### Proof commands (certification gate)

```bash
# Per platform standalone
pytest tests/programs/<platform>/ -q
pytest tests/integration/test_<platform>_postgres.py -q

# Institutional++ full certification
make fg-certification
# Runs: unit + postgres + load smoke + chaos + chain verify
```

---

## Failure mode matrix (operational gold standard)

| Failure | Detection | Automated response | Operator action |
|---------|-----------|-------------------|-----------------|
| Redis outage | `guardrail_degraded_total` | Local fallback limits | Restore Redis; monitor per-pod |
| Invariant violation | `regulatory_audit_violation_total` | Diagnostic mode: writes 503 | Fix data; `POST /internal/diagnostic/clear` |
| Ledger tampering | `chain_verification_failed_total` | CronJob fails, page | Forensics on events table |
| Reconciler partition | `reconciler_leader == 0` | Standby idle | Check advisory lock |
| Feed degradation | `feed_degraded_total` | AlgoFreeze → DEGRADED → FROZEN | Restore feed; manual unfreeze |
| Inference rail storm | `rail_circuit_open_total` | Block dispatch | Failover rail |
| FX API unavailable | `fx_snapshot_failed_total` | SubledgerSync strand, no guess | Wait for authoritative rate |

---

## CronJob probe suite (production)

| Job | Schedule | Purpose |
|-----|----------|---------|
| `synthetic-canary` | */5 | Liveness all services |
| `governance-canary` | */10 | Diagnostic + verify-chain |
| `ledger-chain-verify` | hourly | Hash integrity |
| `ledger-chain-anchor` | hourly :15 | S3 Object Lock head |
| `algofreeze-version-probe` | */15 | Runtime SHA vs approved |
| `wirematch-golden-record-drift` | daily | Embedding baseline check |

---

## HA topology (production institutional++)

| Component | Minimum | Gold standard |
|-----------|---------|---------------|
| Platform / sidecar | 2 replicas | 3–12 HPA, PDB, anti-affinity |
| Gateway | 2 | OIDC at edge |
| Reconciler | 2 | Leader election |
| Postgres | Managed HA | RDS Multi-AZ / Cloud SQL HA |
| PgBouncer | 3 | Transaction pooling |
| Redis | 1 (dev) | Sentinel: 1 master + 1 replica + 3 sentinels |

Enterprise overlay: Istio STRICT mTLS, egress allowlist for inference rails / FX APIs only.

---

## Diligence proof pack (what examiners and CISOs receive)

| Artifact | Proves |
|----------|--------|
| `make <platform>-demo` recording | Pre-execution control works |
| Invariant report (`generate_invariant_report.py`) | Zero violations in test run |
| Prometheus scrape export | SLO counters live |
| Chain verify API response | Tamper evidence |
| S3 anchor head hash | External immutability |
| Chaos test CI log | Survives partition |
| `docs/operations-runbook.md` | Operator readiness |
| Regulatory mapping table (this doc) | Compliance alignment |

---

## Quality bar — merge gate

Every Finance Governor PR must answer (from ModelGovernor `docs/quality-bar.md`):

1. What institutional capability does this improve?
2. What are the failure modes?
3. How is idempotency / replay handled?
4. How is auditability preserved?
5. How is this monitored, repaired, or reconciled?
6. Does standalone mode still work without spine?

**Merge rule:** Credible, deterministic, auditable, robust — or it does not ship.

---

## Institutional++ vs "enterprise SaaS"

| Typical enterprise SaaS | Finance Governor institutional++ |
|-------------------------|----------------------------------|
| 99.9% API uptime | 99.5% gate + **zero** invariant budget |
| Centralized logging | Append-only hash-chained events |
| Manual reconciliation UI | Automated reconciler + strand semantics |
| Feature flags in monolith | Standalone platforms, optional spine |
| Post-hoc analytics | Pre-execution gate |
| "SOC2 in progress" | Probe suite + chaos harness in CI |

---

## Certification levels (product packaging)

| Level | Name | Requirements |
|-------|------|--------------|
| **L1** | Platform Ready | Standalone demo + Tier 1–2 tests |
| **L2** | Institutional | L1 + diagnostic mode + invariants + metrics |
| **L3** | Institutional++ | L2 + hash chain + SLO alerts + Tier 3 load |
| **L4** | Gold | L3 + Tier 4 chaos + K8s HA + S3 anchor + OIDC |

ModelGovernor production packaging is **L3–L4**. Each Finance Governor platform targets **L2** at first standalone ship, **L4** when spine-connected in enterprise overlay.

---

## Related

- [desirability.md](desirability.md) — why buyers want this
- [capability-matrix.md](capability-matrix.md) — RFP checklist
- [platform-model.md](platform-model.md) — standalone vs spine
- ModelGovernor: `docs/institutional-reliability.md`, `docs/quality-bar.md`, `docs/slo-definitions.md`
