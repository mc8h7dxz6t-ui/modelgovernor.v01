# Governor Portfolio — Sales Sheet (Spec + Tech Edge)

**As-of:** institutional++ packaging across ModelGovernor, Finance Governor, Insurance Governor, Cybersecurity Governor.  
**Use:** acquirer decks, technical-founder IP sales, design-partner scoping — **not** enterprise procurement as turnkey vendor.

**Maturity principle:** Implementation, not intent. Full scorecard: [operational-architecture-scorecard.md](../governor-spine-core/docs/operational-architecture-scorecard.md).

---

## Operational architecture scorecard

```
[ IDEAL GOLD STANDARD ] ══════════════════════════════════════════► 10/10

[ REPOSITORY IMPLEMENTATION STATE ]
• Core Transaction Kernel ──────────────────────► 8.5/10
• ModelGovernor AI Spend Platform ──────────────► 7.0/10
• Finance / Cyber / Insurance Wedges ───────────► 6.0/10
• Combined Portfolio Readiness ─────────────────► 6.5/10  (credible source-code asset)
```

**Verdict:** Pre-hardened **control-plane IP** — not a completed corporate software business with audits and 24×7 support.

---

## Exit positioning

| Path | Motion | Outcome |
|------|--------|---------|
| **Fantasy** | Pitch L5 12-SKU enterprise platform as vendor-of-record | Blocked by procurement, SOC2, references, SLAs |
| **Realistic** | Pitch pre-hardened **source-code IP sale** to technical founders / acquirer engineering | Matches 6.5/10 asset; `make plug` + L4 CI as proof |

---

## Sale readiness verdict

| Motion | Ready? | Proof |
|--------|--------|-------|
| **Demo / first call (Mode A — single VPC)** | **Yes** | `make demo-gold`, `make plug`, `make cg-egress-wedge-demo` |
| **Design-partner pilot (Mode B — buyer VPC)** | **Yes with scoping** | MG + CG spine + 1–2 wedges; K8s overlays; buyer operates |
| **Vendor-of-record production** | **No** (without operating company) | No SOC2/ISO from repo; no support org — buyer or partner must own ops |
| **Integration scaffolds** | **Spec only** | FG: SubledgerSync, AssetLedger, CreditGovern — connector SOW |

**Cyber wedges:** nine platforms in canonical tree — six sales SKUs plus ThreatProxy, IR gate, ComplianceLogger (thin FastAPI wedges; spine carries the IP).

**Honest CG pitch:** *Tamper-evident authorization ledger for security commits* — not a Fortune 500 cyber suite.

**Mode A rule:** Almost every “concern” in diligence is **config, buyer credential, or SOW** — not missing spine IP. See [Deployment concern matrix](#deployment-concern-matrix) below.

---

## Deployment concern matrix

How buyer objections map to **Single VPC pilot (A)** vs **Multi-instance production (B)**.

| # | Concern | Mode A (single VPC) | Mode B (multi-instance) | Real blocker? |
|---|---------|---------------------|-------------------------|---------------|
| 2 | **Proxy** — Redis | ✅ Works | Needs `INST_REDIS_URL` / Sentinel | **No** — config |
| 3 | **Alt-Data** — buyer feeds | ✅ Demo feed | Custom feed = mapping SOW | **Inherent** to alt-data business, not spine |
| 4 | **AI Kit** — live LLM | ✅ Stub/trace | `--live-llm` + buyer API key | **No** — buyer credential |
| 5 | **Webhook Mesh** — delivery | ✅ Background queue | Redis for durable delivery | **No** — config |
| 6 | **Ad Guard** — Redis | ✅ Single instance | Redis multi-instance | **No** — config |
| 7 | **Health** — hospital BAA | ✅ Ingest/serve/export | Signed BAA + ward go-live | **Legal/process** — template ≠ signed BAA |
| 9 | **Drift Gate** — rolling state | ✅ File-backed state | `INST_REDIS_URL` for shared rolling | **No** — config |
| 11 | **Spend Guard** — CI depth | ✅ CLI + gateway rigorous | K8s/Postgres compose = north star | **No for A**; compose optional |

**Sales line:** *“Nothing in this matrix blocks a pilot. Mode B is Redis URL, Sentinel, and your signatures — not a rebuild.”*

---

## Shared spine IP (all three governors)

| Capability | Tech edge vs market |
|------------|---------------------|
| **Crystallize → act → commit** | Competitors **observe after**; we **enforce before** irreversible action |
| **Append-only hash chain** | LiteLLM/Portkey log requests; we **seal events** + verify CronJob + S3 anchor |
| **STRANDED semantics** | Timeouts → ambiguous hold, not silent wrong state (Knight/Citigroup/hijack class) |
| **Reconciler + leader election** | HA sweep without dual-write; chaos-tested (Toxiproxy) |
| **Diagnostic mode** | Writes halt, reads continue — **no poison pill** (vs circuit breakers that brick prod) |
| **Standalone OR spine** | Days-to-weeks wedge deploy; spine optional upsell |

---

# The four governors

## MG-SPINE — ModelGovernor

**Buyer:** VP AI Platform, FinOps, enterprise architects  
**One line:** Ledger-backed **reserve-before-dispatch** for LLM/agent spend.

| vs Competitor | What they do | **Our tech edge** |
|---------------|--------------|-------------------|
| **LiteLLM** | OSS proxy; enterprise = keys, budgets, logs | **Reserve → settle** ledger; reconciler; stranded holds; not routing-only |
| **Portkey** (~$100K/yr enterprise) | Managed gateway, guardrails, caching | **Pre-dispatch enforcement** + tamper-evident chain; they optimize routing |
| **Helicone** | Fast observability / gateway | **Control plane**, not dashboard; wallet lockout on drift |
| **Cloud budget alerts** | Post-hoc spend alerts | **Atomic per-trace caps** before provider call |
| **Homegrown wrappers** | Ad-hoc middleware | **57+ tests**, chaos harness, K8s production overlays |

**Unique primitive:** Reserve-before-dispatch + drift lockout + hash-chained `ledger_events`.

**Demo:** `make demo-gold` · **SKU codes:** `MG-PLATFORM-DEMO`, `STAGING`, `PRODUCTION`, `ADDON-ENTERPRISE-SECURITY`

---

## FG-SPINE — Finance Governor

**Buyer:** CRO, CFO, Treasurer, Model Risk  
**One line:** **Crystal Commit Protocol (CCP)** — no financial surprise commits without a governance crystal.

| vs Competitor | What they do | **Our tech edge** |
|---------------|--------------|-------------------|
| **ServiceNow GRC / Archer** | Policy registers | **Runtime** freeze/gate/reserve — not paperwork |
| **BlackLine / Duco** | Month-end reconcile | **Match at clear** + FX snapshot hash (SubledgerSync) |
| **ValidMind / ModelOp** | MRM validation docs | **Reserve-before-score** at inference time (CreditGovern) |
| **Payment hubs (Finastra, FIS)** | Own the rail | **Pre-rail semantic + Decimal gate** (WireMatch) — wedge, not replacement |
| **EMS / exchange kill switches** | Blunt halt | **Version SHA + feed heartbeat** proxy freeze (AlgoFreeze) |

**Unique primitive:** CCP — Governance Crystal + Commit Horizon + Crystal Mesh (e.g. no wire while desk FROZEN).

**Demo:** `make fg-stack-up` + `make crystal-demo` · **Pairs with:** `FG-ALGOFREEZE`, `FG-WIREMATCH`, etc.

---

## CG-SPINE — Cybersecurity Governor

**Buyer:** CISO, SOC lead, zero-trust architects  
**One line:** **Threat Crystal Protocol (TCP)** — tamper-evident authorization ledger for security commits.

| vs Category | What incumbents do | **What we actually ship** |
|-------------|-------------------|---------------------------|
| **SIEM** | Correlate probabilistic alerts | **Deterministic crystallize-before-commit** + hash chain proof |
| **XDR / EDR** | Endpoint detection | **Mesh blocks egress/IR commits** when parent state is VIOLATION/DRIFT/BLOCKED |
| **IdP / IGA** | Identity lifecycle | **Session arm + mesh parent** — integration wedge, not Okta replacement |
| **Network DLP / proxy** | Inline byte policy | **EgressGovern allowlist + Envoy ext_authz adapter** — wire to your proxy |
| **CNAPP** | Cloud posture alerts | **PostureReconcile drift → mesh block** — not a cloud graph |

**Unique primitive:** TCP + Threat Mesh + append-only security chain + optional S3 anchor.

**Defensible demo (no apology):** `make cg-egress-wedge-demo` — identity arm → mesh blocks bad egress commit → Envoy ext_authz denies off-allowlist host → `verify-chain`.

**Full multi-SKU story:** `make cg-security-demo` · **Pairs with:** wedges below.

---

## IG-SPINE — Insurance Governor (6.0/10 wedge band)

**Buyer:** Chief Claims Officer, MGA platform lead  
**One line:** Claim Crystal Protocol — governed reserve + hash-chained indemnity commits.

| vs Category | Incumbents | **What we ship** |
|-------------|-----------|------------------|
| Core PAS | Guidewire system of record | Runtime gate — ClaimGate wedge, not PAS replacement |
| FNOL integrations | Live vendor connectors | Webhook **shape normalizers** — production connector = SOW |
| Payment rail | FedNow live | ACH stub default; live rail = buyer credentials |

**Demo:** `make ig-stack-up` + ClaimGate · **Sheet:** [insurance-governor-production.md](insurance-governor-production.md)

---

# The product codes

## ModelGovernor deployment SKUs (4)

### `MG-PLATFORM-DEMO`
- **Does:** Docker-only mock providers; 11-step institutional++ walkthrough.
- **vs:** LiteLLM local dev — **full ledger + reconciler + drift drill**, not proxy-only.
- **Status:** ✅ Shipped · `make demo-gold`

### `MG-PLATFORM-STAGING`
- **Does:** Customer VPC pilot; live providers; ESO; 2+ sidecar replicas.
- **vs:** Portkey Pro — **buyer-owned VPC**, hash chain, no log-volume tax.
- **Status:** ✅ Manifests + CI

### `MG-PLATFORM-PRODUCTION`
- **Does:** Sentinel, PgBouncer, OIDC, S3 anchor, CronJobs, SLO alerts.
- **vs:** Cloud-native FinOps — **pre-execution** + examiner-grade anchor.
- **Status:** ✅ Overlay shipped

### `MG-ADDON-ENTERPRISE-SECURITY`
- **Does:** Istio STRICT mTLS, LLM egress allowlist.
- **vs:** Generic service mesh — **LLM-specific egress policy** templates.
- **Status:** ✅ Enterprise overlay (bundled in prod)

---

## Finance Governor wedges (5)

### `FG-ALGOFREEZE` ✅ Demo-ready
- **Does:** Version guard + feed heartbeat → proxy freeze before EMS/exchange egress.
- **vs:** Exchange kill switch — **deploy SHA vs approved registry**; vs surveillance — **pre-egress**, not post-trade.
- **Tech edge:** `FROZEN` = zero egress hard invariant; sub-100ms target; freeze events hash-chained.
- **ROI narrative:** Knight-class ($440M) prevention.

### `FG-WIREMATCH` ✅ Demo-ready
- **Does:** Semantic beneficiary match + `Decimal`-only amounts → HELD/REJECTED before rail.
- **vs:** SWIFT schema tools — **intent matching**; vs AML screening — **fat-finger class**, not sanctions.
- **Tech edge:** No float path; spine `reserve` → `settle` on funds; golden record version pinned in crystal.
- **ROI narrative:** Citigroup-class ($900M) prevention.

### `FG-SUBLEDGERSYNC` 📋 Integration scaffold
- **Label:** Technical integration scaffold — engineered for custom extension (not production reconciliation product).
- **Does:** Intercompany match-at-clear with immutable FX snapshot hash.
- **vs:** BlackLine — **event-driven at clear**, not month-end batch.
- **Tech edge:** FX rate hash on every match; spine group invariant (zero orphans after sweep).

### `FG-ASSETLEDGER` 📋 Integration scaffold
- **Label:** Technical integration scaffold — ERP/GL bridge is buyer SOW.
- **Does:** Regulation-version-pinned daily depreciation + append-only charges.
- **vs:** SAP FA module — **examiner-friendly chain**, not batch surprise.
- **Tech edge:** `reg_table_version` in every charge; book value invariant.

### `FG-CREDITGOVERN` 📋 Integration scaffold
- **Label:** Technical integration scaffold — mock scoring rail; wire buyer model HTTP endpoint.
- **Does:** Reserve exposure → score → settle; fair-lending evidence binding.
- **vs:** ValidMind — **sub-second runtime enforcement**; vs Arthur/Fiddler — **pre-score reserve**, not post drift alert.
- **Tech edge:** ModelGovernor-proven reserve/settle/strand ported to credit exposure.

---

## Cybersecurity Governor wedges (9 platforms)

### Sales SKUs (6)

### `CG-IDENTITYGATE` ✅ Shipped
- **Does:** `POST /session/arm` — device fingerprint + IP binding; violation → mesh blocks child commits.
- **vs:** IdP MFA — **crystal-bound commit gate**, not seat-based IGA.
- **Tech edge:** Fingerprint mismatch strands at authorize via Threat Mesh parent.
- **Port:** 8124

### `CG-EGRESSLOCK` ✅ Shipped — **defensible wedge**
- **Does:** `POST /egress/evaluate` + `POST /envoy/authz/check` — allowlist before bytes leave.
- **vs:** Corporate HTTP proxy — **mesh-aware** (parent VIOLATION blocks egress commit).
- **Tech edge:** Envoy ext_authz adapter; governed commit with exposure facets.
- **Demo:** `make cg-egress-wedge-demo` · **Port:** 8123

### `CG-WITNESSBRIDGE` ✅ Shipped
- **Does:** Okta / CloudTrail / generic ingest; critical events witnessed + crystallized.
- **vs:** SIEM ingestion — **log erasure class** events get crystals at witness time.
- **Tech edge:** DeleteTrail-class events → critical crystal; silence detection path.
- **Port:** 8129

### `CG-LINEAGEINGEST` ✅ Shipped
- **Does:** Falco / Tetragon / generic → `lineage_edges` structural DAG.
- **vs:** CNAPP alerts — **crystal-bound lineage** for forensic reconstruct.
- **Tech edge:** Parent/child edges feed Threat Mesh.
- **Port:** 8130

### `CG-POSTURERECONCILE` ✅ Shipped
- **Does:** `POST /posture/evaluate` (alias `/posture/ingest`) — CVE/patch lag vs tolerance.
- **vs:** Posture dashboards — **authorize-time mesh block**, not alert backlog.
- **Tech edge:** Critical control drift → mesh blocks egress/content commits.
- **Demo:** `make posture-reconcile-demo` · **Port:** 8127

### `CG-CONTENTGUARD` ✅ Shipped
- **Does:** `POST /content/evaluate` — PII/secret pattern gate before publish.
- **vs:** Edge DLP only — **pre-publish crystal** + mesh blocks egress on BLOCKED.
- **Demo:** `make content-guard-demo` · **Port:** 8131

### Spine-adjacent platforms (3) — thin wedges, honest pricing

### `CG-THREATPROXY` ✅ Shipped (not on original sales sheet)
- **Does:** `POST /threat/score` — pre-dispatch threat score gate.
- **Reality:** ~80-line FastAPI wedge; mesh blocks downstream IR on BLOCKED.
- **Port:** 8125 · **List ACV:** $40K – $90K (add-on)

### `CG-IRGATE` ✅ Shipped
- **Does:** `POST /ir/authorize` — playbook action authorization crystal.
- **Reality:** Thin gate; value is mesh + chain, not SOAR replacement.
- **Port:** 8126 · **List ACV:** $50K – $120K (add-on)

### `CG-COMPLIANCELOGGER` ✅ Shipped
- **Does:** Regulatory evidence export + sealed facets.
- **Reality:** Export path + chain binding; not GRC workflow replacement.
- **Port:** 8128 · **List ACV:** $40K – $100K (add-on)

---

# Extended catalog (concern matrix products)

These share the **same spine pattern**; Mode A sale-ready per matrix above.

| # | Code (suggested) | Role | Tech edge vs market |
|---|------------------|------|---------------------|
| 2 | `MG-PROXY` / Spend routing | LLM proxy + governance | Reserve-before-dispatch (see MG-SPINE) |
| 3 | `MG-ALTDATA` | Alternative data feeds | Crystal-bound ingest + demo feed; custom = SOW |
| 4 | `MG-AIKIT` | AI dev kit / trace | Stub/trace default; live = buyer key — same ledger semantics |
| 5 | `MG-WEBHOOK-MESH` | Durable webhook delivery | Redis streams queue; vs raw HTTP — **retry + spine audit** |
| 6 | `MG-ADGUARD` | Ad / content guard | Policy gate before publish; Redis-backed state |
| 7 | `MG-HEALTH` | Healthcare ingest/export | BAA template + ingest/serve; **signed BAA = buyer legal** |
| 9 | `MG-DRIFTGATE` | Model/output drift | Rolling window + lockout; shared Redis for multi-instance |
| 11 | `MG-SPENDGUARD` | Spend enforcement | Same as ModelGovernor core — drift + wallet lockout |

---

# Pricing (list — separate from spec)

*Illustrative first-deal list; expect 15–35% discount on multi-year.*

## Per-SKU annual list (USD)

| Code | List ACV |
|------|----------|
| `MG-PLATFORM-DEMO` | $0 – $25K workshop |
| `MG-PLATFORM-STAGING` | $120K – $250K |
| `MG-PLATFORM-PRODUCTION` | $350K – $900K |
| `MG-ADDON-ENTERPRISE-SECURITY` | +$80K – $200K |
| `FG-SPINE` | $200K – $400K |
| `FG-ALGOFREEZE` | $150K – $400K |
| `FG-WIREMATCH` | $200K – $500K |
| `FG-SUBLEDGERSYNC` | $150K – $350K |
| `FG-ASSETLEDGER` | $100K – $250K |
| `FG-CREDITGOVERN` | $250K – $600K |
| `CG-SPINE` | $120K – $280K |
| `CG-IDENTITYGATE` | $60K – $140K |
| `CG-EGRESSLOCK` | $80K – $180K |
| `CG-WITNESSBRIDGE` | $50K – $120K |
| `CG-LINEAGEINGEST` | $50K – $110K |
| `CG-POSTURERECONCILE` | $60K – $130K |
| `CG-CONTENTGUARD` | $50K – $120K |
| `CG-THREATPROXY` | $40K – $90K |
| `CG-IRGATE` | $50K – $120K |
| `CG-COMPLIANCELOGGER` | $40K – $100K |

*Platform wedges are thin FastAPI services; price the **spine + mesh + chain** — not six pretend Fortune 500 products.*

## Bundle list

| Bundle | List ACV | Notes |
|--------|----------|-------|
| AI Governance Enterprise (MG prod + security) | $430K – $1.1M | |
| Finance Risk Critical (FG spine + AlgoFreeze + WireMatch) | $500K – $1.0M | |
| Cyber spine + EgressLock wedge (pilot) | $180K – $380K | **Recommended first deal** |
| Cyber Institutional++ (CG spine + 6 sales SKUs) | $350K – $750K | Not $700K–$1.4M until dataplane SOW |
| Tri-Governor Portfolio | $800K – $1.6M | |

## Market proof points

| Comp | Typical enterprise $ | Honest positioning |
|------|---------------------|-------------------|
| Portkey Enterprise | ~$100K/yr (AWS MP) | MG: ledger + reconciler + anchor |
| LiteLLM Enterprise | Custom $50K–$200K+ | MG: runtime enforcement, not keys-only |
| Corporate HTTP proxy + policy | $50K–$300K/yr | CG: **complement** — ext_authz + commit ledger |
| GRC / evidence tools | $100K–$400K/yr | CG: sealed facets + chain, not workflow |
| BlackLine | $200K–$1M+/yr | FG: pre-execution wedge vs close management |

---

## One-slide competitive moat

```
Incumbents:  event → log → dashboard → human → maybe fix
Governors:   event → CRYSTALLIZE → (allow | freeze | hold | reserve) → commit → prove
```

**Elevator:** *No surprise commits without a crystal — AI spend, finance ops, or security authorize.*

---

## Quick commands

```bash
make demo-gold              # ModelGovernor
make plug                   # Institutional Self-Check (all governors offline)
make compose-smoke-cg       # Live CG stack health + verify-chain (Docker)
make cg-egress-wedge-demo   # Defensible CG wedge (ext_authz + chain verify)
make cg-security-demo       # Multi-SKU CG story
make posture-reconcile-demo # PostureReconcile wedge
make content-guard-demo     # ContentGuard wedge
make algofreeze-demo        # Finance wedge
make wirematch-demo         # Finance wedge
make demo-all-platforms     # Full MG SKU story
```

Related: [plug-and-play.md](../plug-and-play.md) · [cybersecurity-governor/](../../cybersecurity-governor/) · [governor-spine-core/](../../governor-spine-core/README.md)

---

## Technical acquisition narrative (honest)

**Asset type:** Pre-hardened **source-code IP** (portfolio **6.5/10**) — kernel **8.5/10**.

**Say:** Pre-execution transactional kernel — crystallize-before-commit, tamper-evident hash chains, mesh blocks. **L4 Gold** in CI; **Institutional Self-Check** via `make plug` (not SOC2/ISO). Ideal buyer: **technical founder or acquirer engineering team**.

**Do not say:** Turnkey L5 12-SKU enterprise vendor; SOC2 certified; Fortune 500 replacement suite.

**Structure:** Price the **spine kernel**; wedges are **integration scaffolds** unless demo-ready (AlgoFreeze, WireMatch, EgressGovern, ClaimGate).

**Verification:** `make plug` · `make compose-smoke-cg` · per-governor `verify-chain` · [operational-architecture-scorecard.md](../governor-spine-core/docs/operational-architecture-scorecard.md)
