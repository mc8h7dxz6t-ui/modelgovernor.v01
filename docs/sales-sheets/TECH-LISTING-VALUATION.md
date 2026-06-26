# Governor Portfolio — Tech Listing & Valuation (No Pricing)

**As-of:** institutional++ packaging across ModelGovernor, Finance Governor, Cybersecurity Governor.  
**Use:** listing pages, investor memos, RFP technical annexes, IP diligence.  
**Excludes:** list prices, ACV tables, sport/trading positioning.

**Methodology:** [valuation-pre-revenue.md](valuation-pre-revenue.md) — replacement cost (40%) + differentiation premium (35%) + commercial readiness (25%). Figures are **illustrative technical asset worth**, not appraisals or company valuation.

---

## Master listing

| Code | Product | Governor | Category | Demo status | Proof |
|------|---------|----------|----------|-------------|-------|
| `MG-SPINE` | ModelGovernor control plane | ModelGovernor | AI spend governance | ✅ | `make demo-gold` · 57+ tests · 4-tier CI |
| `MG-PLATFORM-DEMO` | Sales demo stack | ModelGovernor | Deployment SKU | ✅ | Docker mock providers · 11 steps |
| `MG-PLATFORM-STAGING` | Customer VPC pilot | ModelGovernor | Deployment SKU | ✅ | K8s overlay + ESO |
| `MG-PLATFORM-PRODUCTION` | Production institutional++ | ModelGovernor | Deployment SKU | ✅ | Sentinel · OIDC · S3 anchor · CronJobs |
| `MG-ADDON-ENTERPRISE-SECURITY` | Istio mTLS + LLM egress allowlist | ModelGovernor | Security add-on | ✅ | Enterprise overlay |
| `FG-SPINE` | Finance Governor control plane | Finance | Regulated ops governance | ✅ | `make fg-demo-gold` · 55+ tests |
| `FG-ALGOFREEZE` | Execution version & feed guard | Finance | Wedge | ✅ demo-ready | `make algofreeze-demo` |
| `FG-WIREMATCH` | Semantic payment gate | Finance | Wedge | ✅ demo-ready | `make wirematch-demo` |
| `FG-SUBLEDGERSYNC` | Intercompany match-at-clear | Finance | Wedge | 📋 design-partner | `make subledger-demo` |
| `FG-ASSETLEDGER` | Regulation-pinned depreciation | Finance | Wedge | 📋 design-partner | `make assetledger-demo` |
| `FG-CREDITGOVERN` | Reserve-before-score credit gate | Finance | Wedge | 📋 design-partner | `make credit-demo` |
| `CG-SPINE` | Cybersecurity Governor control plane | Cyber | Security ops governance | ✅ | `make cg-security-demo` · 70+ tests |
| `CG-IDENTITYGATE` | Session arm + device binding | Cyber | Wedge | ✅ shipped | `make identity-gate-demo` |
| `CG-EGRESSLOCK` | Egress evaluate gate | Cyber | Wedge | ✅ shipped | `make egress-lock-demo` |
| `CG-WITNESSBRIDGE` | Universal witness ingest | Cyber | Wedge | ✅ shipped | `make witness-bridge-demo` |
| `CG-LINEAGEINGEST` | Structural lineage DAG | Cyber | Wedge | ✅ shipped | `make lineage-ingest-demo` |
| `CG-POSTURERECONCILE` | Posture vs baseline gate | Cyber | Wedge | ✅ shipped | `make posture-reconcile-demo` |
| `CG-CONTENTGUARD` | Pre-publish content gate | Cyber | Wedge | ✅ shipped | `make content-guard-demo` |
| `MG-PROXY` | LLM proxy + governance | ModelGovernor | Extended catalog | ✅ | Same as MG-SPINE |
| `MG-ALTDATA` | Alternative data ingest | ModelGovernor | Extended catalog | ✅ Mode A | Crystal-bound ingest |
| `MG-AIKIT` | AI dev kit / trace | ModelGovernor | Extended catalog | ✅ Mode A | Stub/trace default |
| `MG-WEBHOOK-MESH` | Durable webhook delivery | ModelGovernor | Extended catalog | ✅ Mode A | Redis streams + audit |
| `MG-ADGUARD` | Ad / content policy gate | ModelGovernor | Extended catalog | ✅ Mode A | Pre-publish policy |
| `MG-HEALTH` | Healthcare ingest/export | ModelGovernor | Extended catalog | ✅ Mode A | BAA template path |
| `MG-DRIFTGATE` | Model/output drift lockout | ModelGovernor | Extended catalog | ✅ | `demo-gold` step 10 |
| `MG-SPENDGUARD` | Spend enforcement core | ModelGovernor | Extended catalog | ✅ | Wallet lockout + reserve |

---

## Shared spine IP (all governors)

| Primitive | Technical specification | Competitive edge |
|-----------|-------------------------|------------------|
| **Crystallize → act → commit** | Immutable snapshot at arm time; irreversible action requires bound crystal ID | Incumbents observe **after**; governors enforce **before** |
| **Append-only hash chain** | `ledger_events` / `decision_events` / `security_events` + verify API + optional S3 Object Lock anchor | Log stores lack tamper-evident proof |
| **STRANDED semantics** | Timeout/ambiguity → held state, never silent wrong commit | Retry-heavy systems rewrite or guess |
| **Reconciler + leader election** | Horizon sweep, stranded repair, `RECONCILED_LATE_SETTLE` without history rewrite | HA without dual-write; chaos-tested |
| **Diagnostic mode** | Writes halt, reads continue — no poison pill | Circuit breakers often brick production |
| **Threat / Crystal Mesh** | Cross-platform invariants (e.g. STRANDED identity blocks egress commit) | Point tools lack shared authorize-time fabric |
| **Standalone OR spine** | `*_SPINE_ENABLED=false` per platform; days-to-weeks wedge deploy | Suites force all-or-nothing |

**Elevator:** *No surprise commit without a crystal — AI spend, finance ops, or security authorize.*

---

# Deep dive — ModelGovernor (`MG-SPINE`)

**Buyer:** VP AI Platform, FinOps, enterprise architects  
**One line:** Ledger-backed **reserve-before-dispatch** for LLM and agent spend.

## Technical specification

| Layer | Components | Ports (default) |
|-------|------------|-----------------|
| Gateway | Provider routing, OpenAI-compat API, OIDC termination | 8080 |
| Sidecar | Reserve, settle, policy, ledger, drift lockout | 8081 |
| Reconciler | Leader-elected horizon sweep, stranded holds | 8082 |
| Data | PostgreSQL (authoritative), Redis (guardrails / diagnostic latch) | 5432, 6379 |

| Capability | Spec detail |
|------------|-------------|
| Reserve-before-dispatch | Atomic per-trace cap before provider call |
| Settlement | Micro-cent `NUMERIC(24,12)` pricing; idempotent lifecycle |
| Drift enforcement | Rolling window → wallet lockout (demo step 10) |
| Audit | Hash-chained events; hourly verify CronJob; S3 anchor |
| HA / prod | PgBouncer, Redis Sentinel, ExternalSecrets, Prometheus SLOs |
| Security pack | Istio STRICT mTLS, LLM egress allowlist |

## Competitive edge

| vs | They do | Our edge |
|----|---------|----------|
| LiteLLM | Proxy, keys, budgets, logs | Reserve → settle ledger; reconciler; stranded holds |
| Portkey | Managed gateway, guardrails, caching | Pre-dispatch enforcement + tamper-evident chain |
| Helicone | Observability / gateway | Control plane, not dashboard |
| Cloud budget alerts | Post-hoc spend alerts | Atomic caps **before** provider call |
| Homegrown wrappers | Ad-hoc middleware | 57+ tests, Toxiproxy chaos, K8s overlays |

## Technical valuation

| Lens | Assessment |
|------|------------|
| **Replacement cost** | 12–18 eng-mo production stack + 10–14 eng-mo cross-cutting IP ≈ **$400K–$710K** build |
| **Differentiation premium** | Rare combo: financial invariant suite + reconciler HA + hash anchor in AI gateway category |
| **Readiness premium** | 4-tier CI, GitOps manifests, demo-gold — sale-ready Mode A/B/C |
| **Asset worth (MG platform bundle)** | **$3.5M–$6.0M** fair · **$8.5M** strategic ceiling |
| **Moat score (1–5)** | **4.5** — proven engineering; category still forming |

---

# Deep dive — Finance Governor (`FG-SPINE`)

**Buyer:** CRO, CFO, Treasurer, Model Risk  
**One line:** **Crystal Commit Protocol (CCP)** — no regulated financial surprise commit without a governance crystal.

## Technical specification

| Layer | Components | Ports (default) |
|-------|------------|-----------------|
| Gateway | Governed commit, crystallize proxy | 8090 |
| Sidecar | CCP, commit escrow, exposure budget, regulatory_ops | 8091 |
| Reconciler | Commit horizon sweep, crystal repair | 8092 |
| Data | PostgreSQL, Redis | 5443, 6389 |

| CCP primitive | Spec detail |
|---------------|-------------|
| Governance Crystal | Hash-chained snapshot at gate/freeze/reserve time |
| Commit Horizon | Risk-tiered TTL → STRAND on ambiguity |
| Crystal-Bound Commit | No irreversible action without `crystal_id` |
| Crystal Mesh | Parent/child crystals across platforms (e.g. no wire while desk FROZEN) |

## Wedges (finance)

### `FG-ALGOFREEZE` — Execution version & feed guard ✅

| | |
|--|--|
| **Does** | Runtime SHA vs approved registry + feed heartbeat → operational FREEZE before outbound automated action |
| **vs** | Blunt kill switches — not deploy-version aware; infra circuit breakers — no approved-version registry |
| **Tech edge** | `FROZEN` = zero egress hard invariant; sub-100ms target; freeze events hash-chained |
| **Use class** | Erroneous deployment / stale feed prevention before high-value automated outbound ops (treasury automation, payment robots, scoring pipelines) — **not** a market-access or execution venue product |

### `FG-WIREMATCH` — Semantic payment gate ✅

| | |
|--|--|
| **Does** | Beneficiary semantic match + `Decimal`-only amounts → HELD/REJECTED before payment rail |
| **vs** | Schema validators — weak intent matching; AML screening — different problem class |
| **Tech edge** | No float path; spine reserve → settle on funds; golden record pinned in crystal |
| **Use class** | Fat-finger / wrong-beneficiary prevention at pre-rail gate |

### `FG-SUBLEDGERSYNC` — Intercompany match-at-clear 📋

| | |
|--|--|
| **Does** | Event-driven IC match with immutable FX snapshot hash |
| **vs** | Close management suites — batch month-end mindset |
| **Tech edge** | FX rate hash on every match; spine group invariant (zero orphans after sweep) |

### `FG-ASSETLEDGER` — Regulation-pinned depreciation 📋

| | |
|--|--|
| **Does** | Daily depreciation with `reg_table_version` in every charge |
| **vs** | ERP FA modules — weak append-only audit chain |
| **Tech edge** | Book value invariant; examiner-friendly event chain |

### `FG-CREDITGOVERN` — Reserve-before-score 📋

| | |
|--|--|
| **Does** | Reserve exposure → score → settle; fair-lending evidence binding |
| **vs** | MRM doc platforms — not sub-second runtime enforcement; observability tools — post-inference only |
| **Tech edge** | ModelGovernor-proven reserve/settle/strand ported to credit exposure |

## Competitive edge (spine)

| vs | They do | Our edge |
|----|---------|----------|
| ServiceNow GRC / Archer | Policy registers | Runtime freeze/gate/reserve |
| BlackLine / Duco | Month-end reconcile | Match at clear + FX snapshot hash |
| ValidMind / ModelOp | MRM validation docs | Reserve-before-score at inference time |
| Payment hubs | Own the rail | Pre-rail semantic + Decimal gate — wedge, not replacement |

## Technical valuation

| SKU / bundle | Shipped depth | Asset worth range |
|--------------|---------------|-------------------|
| `FG-SPINE` + CCP docs + demo-gold | ✅ strong | **$1.2M–$2.2M** |
| `FG-ALGOFREEZE` + `FG-WIREMATCH` | ✅ demo-ready | **$800K–$1.6M** combined |
| `FG-SUBLEDGERSYNC` + `FG-CREDITGOVERN` | 📋 runnable, design-partner | **$400K–$900K** combined |
| `FG-ASSETLEDGER` | 📋 in-memory demo | **$150K–$350K** |
| **Finance Governor total** | | **$2.5M–$5.0M** |

| Moat dimension | Score (1–5) | Notes |
|----------------|-------------|-------|
| Pre-execution control | **5** | CCP + mesh — rare unified model |
| Engineering proof | **3.5** | 55 tests local; no FG CI gate on main yet |
| Integration depth | **2.5** | Gate layer, not ERP/rail replacement |
| GTM readiness (2 wedges) | **4** | AlgoFreeze + WireMatch first-call ready |

---

# Deep dive — Cybersecurity Governor (`CG-SPINE`)

**Buyer:** CISO, SOC lead, zero-trust architects  
**One line:** **Threat Crystal Protocol (TCP)** — authorize only with cryptographic crystals; close the Shadow Gap.

## Technical specification

| Layer | Components | Ports (default) |
|-------|------------|-----------------|
| Gateway | Governed security commit | 8100 |
| Sidecar | TCP, action escrow, security_ops, verify-chain | 8101 |
| Reconciler | Session horizon sweep | 8102 |
| Data | PostgreSQL, Redis | 5443, 6390 |

| TCP primitive | Spec detail |
|---------------|-------------|
| Threat Crystal | Immutable hash-chained identity/lineage/posture snapshot |
| Session Horizon | Risk-tiered TTL; ambiguity strands |
| Threat Mesh | Cross-platform blocks (STRANDED session → egress commit denied) |
| Witness quorum | S3 Object Lock + `security_chain_anchors` |
| Lineage DAG | Structural parent/child edges (Falco/Tetragon/generic) |

## Wedges (cyber) — all ✅ shipped

| Code | API / role | Tech edge vs market |
|------|------------|---------------------|
| `CG-IDENTITYGATE` | `POST /session/arm` | Crystal-bound commit; hijack → STRANDED (not alert-only) |
| `CG-EGRESSLOCK` | `POST /egress/evaluate` | Mesh-aware — STRANDED identity blocks egress commit |
| `CG-WITNESSBRIDGE` | `POST /ingest/{source}` | Erasure detection + crystal at witness time |
| `CG-LINEAGEINGEST` | Falco/Tetragon/generic | Structural DAG, not ML correlation |
| `CG-POSTURERECONCILE` | `POST /posture/evaluate` | Authorize-time STRAND vs alert backlog |
| `CG-CONTENTGUARD` | `POST /content/evaluate` | Pre-publish crystal + mesh blocks on BLOCKED |

## Competitive edge

| vs | They do | Our edge |
|----|---------|----------|
| SIEM | Probabilistic correlation | Deterministic crystallize-before-authorize |
| XDR / EDR | Endpoint detection | Governance layer; mesh blocks commit |
| Okta / IGA | Identity lifecycle | Session arm + device binding crystal |
| Zscaler DLP | Network egress policy | EgressLock + Threat Mesh at commit time |
| CNAPP | Posture alerts | LineageIngest + PostureReconcile at authorize |

## Technical valuation

| SKU / bundle | Shipped depth | Asset worth range |
|--------------|---------------|-------------------|
| `CG-SPINE` + TCP | ✅ strong | **$1.5M–$2.8M** |
| Six wedges (all shipped) | ✅ K8s + compose + tests | **$1.2M–$2.4M** |
| Deploy kit (Kustomize 4 overlays) | ✅ minus Helm/ArgoCD | **$400K–$800K** embedded |
| **Cyber Governor total** | | **$3.5M–$6.5M** |

| Moat dimension | Score (1–5) | Notes |
|----------------|-------------|-------|
| Protocol uniqueness (TCP + mesh) | **5** | Shadow Gap narrative is defensible |
| Wedge completeness | **5** | Six platforms shipped vs three in early docs |
| Engineering proof | **4.5** | CI unit + property + Postgres + chaos |
| Packaging / GitOps | **3.5** | Kustomize yes; Helm chart roadmap |

---

# Portfolio valuation summary

## Tri-governor technical asset worth (pre-revenue)

| Bundle | Constituents | Overlap adjustment | **Asset worth** |
|--------|--------------|-------------------|-----------------|
| ModelGovernor enterprise | MG-SPINE + A/B/C/D SKUs | — | **$3.5M–$6.0M** |
| Finance Governor | FG-SPINE + 5 wedges | Shares spine IP with MG | **$2.5M–$5.0M** |
| Cyber Governor | CG-SPINE + 6 wedges | Shares spine IP with MG | **$3.5M–$6.5M** |
| **Portfolio (strategic buyer)** | All three + 25 product codes | −15–25% spine overlap | **$8M–$14M** fair · **$16M** strategic ceiling |

## Valuation drivers (what moves the number)

| Driver | Effect on worth |
|--------|-----------------|
| Named Fortune 500 design-partner logo | +$0.5M–$1.5M narrative |
| First paid pilot (any governor) | Validates 3–5× on that logo's ACV potential |
| FG CI gate + Subledger/Credit promotion to demo-ready | +$0.5M–$1M FG bundle |
| CG Helm + ArgoCD shipped | +$0.3M–$0.6M packaging |
| SOC 2 Type II + pen test letter | +$0.5M–$1M enterprise multiplier |
| Managed multi-tenant SaaS | 2–3× ACV potential (separate agreement) |

## Sale readiness (no pricing)

| Motion | MG | FG | CG |
|--------|----|----|-----|
| Mode A — first-call demo | ✅ | ✅ (spine + 2 wedges lead) | ✅ |
| Mode B — customer VPC pilot | ✅ | ✅ with wiring | ✅ |
| Mode C — production institutional++ | ✅ with IdP/secrets/S3 | ✅ with wiring | ✅ with IdP/vault/S3 |
| CI enforcement on every push | ✅ 4 tiers | ⚠️ local gate | ✅ + chaos |

---

## Quick proof commands

```bash
make demo-gold                    # ModelGovernor
make fg-demo-gold                 # Finance Governor (stack up first)
make cg-security-demo             # Cyber Governor (auto-starts stack)
make demo-all-platforms           # MG full SKU story (live + manifests)
```

## Related documents

- [GOVERNOR-PORTFOLIO.md](GOVERNOR-PORTFOLIO.md) — full competitive copy (includes pricing section)
- [valuation-pre-revenue.md](valuation-pre-revenue.md) — MG-focused methodology
- [05-ip-licensing-framework.md](../05-ip-licensing-framework.md) — licensable primitives
- [capability-matrix.md](../capability-matrix.md) — MG RFP matrix
- [finance-governor/competitive-landscape.md](../finance-governor/competitive-landscape.md)
- [cyber-governor/capability-matrix.md](../cyber-governor/capability-matrix.md)
