# Governor Portfolio — Sales Sheet (Spec + Tech Edge)

**As-of:** institutional++ packaging across ModelGovernor, Finance Governor, Cybersecurity Governor.  
**Use:** investor decks, enterprise RFPs, first-call leave-behinds.

> **Read first:** [HONEST-SCOPE.md](HONEST-SCOPE.md) — canonical readiness tiers (L0–L4), what is shipped vs demo vs delisted.  
> This is **not** twelve independent production-hardened products. It is **one spine pattern**, three governors, and a bounded wedge set.

---

## Sale readiness verdict

| Motion | Ready? | What’s included | Proof |
|--------|--------|-----------------|-------|
| **Demo / first call (Mode A)** | **Yes** | MG demo, CG security demo, 2 FG wedges | `make demo-gold`, `make cg-security-demo`, `make algofreeze-demo` |
| **Paid pilot (Mode B)** | **Yes** | MG + CG spines; FG spine + AlgoFreeze + WireMatch | K8s overlays, ESO, Postgres CI, 55–69+ tests per spine |
| **Production institutional++** | **With wiring** | Postgres + Redis/Sentinel + IdP + optional S3 anchor | `PLUG-AND-PLAY.md` — **not SQLite in prod** |
| **Design-partner only** | **FG L1 wedges** | SubledgerSync, AssetLedger, CreditGovern | Spec + partial tests — no standalone production claim |
| **Do not sell** | **L0 delisted** | MG-HEALTH, MG-ADGUARD, MG-WEBHOOK-MESH standalone | See [HONEST-SCOPE.md](HONEST-SCOPE.md) |

**Shipped today (L4):** CG spine + **six** cyber wedges (`CG-IDENTITYGATE` … `CG-CONTENTGUARD`).  
**Pilot-ready (L3):** MG spine + deployment overlays; FG spine.  
**Demo-ready (L2):** `FG-ALGOFREEZE`, `FG-WIREMATCH`; MG Mode A demo.

---

## Readiness tiers (summary)

| Tier | Count (approx.) | Examples |
|------|-----------------|----------|
| **L4 Shipped** | 7 | CG spine + 6 platforms |
| **L3 Pilot-ready** | 5 | MG spine, FG spine, MG staging/prod overlays |
| **L2 Demo-ready** | 4 | MG demo, FG AlgoFreeze/WireMatch, drift/spend features inside MG |
| **L1 Spec** | 3 | FG SubledgerSync, AssetLedger, CreditGovern |
| **L0 Delisted** | 4+ | Health, Ad Guard, webhook mesh standalone, corp proxy-risk |

Full matrix: [HONEST-SCOPE.md](HONEST-SCOPE.md).

---

## Deployment notes (sellable paths only)

| Concern | Mode A (demo VPC) | Mode B (pilot VPC) | Blocker? |
|---------|-------------------|--------------------|----------|
| **MG reserve/settle** | Docker + **Postgres** | Postgres + Redis/Sentinel | Config / credentials |
| **CG authorize/commit** | Docker + Postgres | HA sidecar + Postgres | Config / IdP |
| **FG wire / algo gate** | Demo stack | Postgres + spine wiring | Integration SOW |
| **Alt-data / webhooks / health** | — | — | **Not standalone SKUs** (delisted or SOW-only) |

**Sales line:** *“We sell one wedge or one spine — Postgres in your VPC — not a twelve-product suite.”*

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

# The three governors

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
**One line:** **Threat Crystal Protocol (TCP)** — authorize only with cryptographic crystals; close the Shadow Gap.

| vs Competitor | What they do | **Our tech edge** |
|---------------|--------------|-------------------|
| **SIEM (Splunk, etc.)** | Correlate probabilistic alerts | **Deterministic crystallize-before-authorize**; chain proof |
| **XDR / EDR** | Endpoint detection | **Governance layer on top** — mesh blocks egress on STRANDED session |
| **Okta / IGA** | Identity lifecycle ($7–14/user/mo) | **Session arm + device binding crystal**; hijack → STRANDED at commit |
| **Zscaler DLP** | Network egress policy | **EgressLock + Threat Mesh** — identity state blocks egress **commit** |
| **CNAPP (Wiz, Prisma)** | Cloud posture alerts | **LineageIngest** structural DAG + crystal-bound facets |

**Unique primitive:** TCP + Threat Mesh + witness quorum (S3 Object Lock) + lineage DAG.

**Demo:** `make cg-security-demo` · **Pairs with:** four cyber wedges below.

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

### `FG-ALGOFREEZE` — **L2** demo-ready
- **Does:** Version guard + feed heartbeat → proxy freeze before EMS/exchange egress.
- **vs:** Exchange kill switch — **deploy SHA vs approved registry**; vs surveillance — **pre-egress**, not post-trade.
- **Tech edge:** `FROZEN` = zero egress hard invariant; sub-100ms target; freeze events hash-chained.
- **ROI narrative:** Knight-class ($440M) prevention.

### `FG-WIREMATCH` — **L2** demo-ready
- **Does:** Semantic beneficiary match + `Decimal`-only amounts → HELD/REJECTED before rail.
- **vs:** SWIFT schema tools — **intent matching**; vs AML screening — **fat-finger class**, not sanctions.
- **Tech edge:** No float path; spine `reserve` → `settle` on funds; golden record version pinned in crystal.
- **ROI narrative:** Citigroup-class ($900M) prevention.

### `FG-SUBLEDGERSYNC` — **L1** design-partner
- **Does:** Intercompany match-at-clear with immutable FX snapshot hash.
- **vs:** BlackLine — **event-driven at clear**, not month-end batch.
- **Tech edge:** FX rate hash on every match; spine group invariant (zero orphans after sweep).

### `FG-ASSETLEDGER` — **L1** design-partner
- **Does:** Regulation-version-pinned daily depreciation + append-only charges.
- **vs:** SAP FA module — **examiner-friendly chain**, not batch surprise.
- **Tech edge:** `reg_table_version` in every charge; book value invariant.

### `FG-CREDITGOVERN` — **L1** design-partner
- **Does:** Reserve exposure → score → settle; fair-lending evidence binding.
- **vs:** ValidMind — **sub-second runtime enforcement**; vs Arthur/Fiddler — **pre-score reserve**, not post drift alert.
- **Tech edge:** ModelGovernor-proven reserve/settle/strand ported to credit exposure.

---

## Cybersecurity Governor wedges (6) — **all L4 shipped**

### `CG-IDENTITYGATE` ✅ Shipped
- **Does:** `POST /session/arm` — device fingerprint + IP binding; hijack → STRANDED.
- **vs:** Okta MFA — **crystal-bound commit**; mismatch strands at authorize, not alert-only.
- **Tech edge:** Fingerprint mismatch blocks commit via TCP; Threat Mesh parent for egress.

### `CG-EGRESSLOCK` ✅ Shipped
- **Does:** `POST /egress/evaluate` — destination/byte policy before bytes leave.
- **vs:** Zscaler DLP — **mesh-aware** (STRANDED identity blocks egress commit).
- **Tech edge:** Governed commit with exposure facets; strand egress NetworkPolicy template.

### `CG-WITNESSBRIDGE` ✅ Shipped
- **Does:** Okta / CloudTrail / generic ingest; critical events witnessed + crystallized.
- **vs:** SIEM ingestion — **log erasure detection** + crystal at witness time.
- **Tech edge:** DeleteTrail-class events → critical crystal; silence detection path.

### `CG-LINEAGEINGEST` ✅ Shipped
- **Does:** Falco / Tetragon / generic → `lineage_edges` structural DAG.
- **vs:** CNAPP alerts — **crystal-bound lineage** for forensic reconstruct.
- **Tech edge:** Parent/child edges feed Threat Mesh; eBPF structural, not ML correlation.

### `CG-POSTURERECONCILE` ✅ Shipped
- **Does:** `POST /posture/evaluate` — live CNAPP/K8s posture vs approved baseline crystal.
- **vs:** Wiz/Prisma dashboards — **authorize-time STRAND**, not alert backlog.
- **Tech edge:** Critical control drift → `STRANDED`; Threat Mesh blocks egress/content commits.
- **Demo:** `make posture-reconcile-demo`

### `CG-CONTENTGUARD` ✅ Shipped
- **Does:** `POST /content/evaluate` — PII/secret pattern gate before publish.
- **vs:** Edge DLP only — **pre-publish crystal** + mesh blocks egress on BLOCKED.
- **Tech edge:** REDACTED path with sealed facets; complements EgressLock byte policy.
- **Demo:** `make content-guard-demo`

---

# Extended catalog — not separate products

**Do not sell these as standalone SKUs.** They are either **features of MG-SPINE**, **L1 demos**, or **delisted**.

| Code | Status | Reality |
|------|--------|---------|
| `MG-PROXY` / `MG-SPENDGUARD` | **MG-SPINE** | Reserve-before-dispatch — same engine, not a second product |
| `MG-DRIFTGATE` | **MG-SPINE** | Demo step 10 — wallet lockout on drift |
| `MG-AIKIT` | L2 | Stub/trace path inside MG; not a separate codebase |
| `MG-ALTDATA` | L1 | Demo feed only; production = mapping SOW |
| `MG-WEBHOOK-MESH` | **L0 delisted** | Partner relay (Svix/Hookdeck); spine audit optional |
| `MG-ADGUARD` | **L0 delisted** | Liability / not production |
| `MG-HEALTH` | **L0 delisted** | No DTAC/FDA path — do not pitch hospitals |

Details: [HONEST-SCOPE.md](HONEST-SCOPE.md).

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
| `CG-SPINE` | $200K – $450K |
| `CG-IDENTITYGATE` | $120K – $300K |
| `CG-EGRESSLOCK` | $150K – $350K |
| `CG-WITNESSBRIDGE` | $100K – $250K |
| `CG-LINEAGEINGEST` | $100K – $200K |
| `CG-POSTURERECONCILE` | $120K – $280K |
| `CG-CONTENTGUARD` | $100K – $250K |

## Bundle list

| Bundle | List ACV |
|--------|----------|
| AI Governance Enterprise (MG prod + security) | $430K – $1.1M |
| Finance Risk Critical (FG spine + AlgoFreeze + WireMatch) | $500K – $1.0M |
| Cyber Institutional++ (CG spine + 6 wedges) | $700K – $1.4M |
| Tri-Governor Portfolio | $1.2M – $2.5M |

## Market proof points

| Comp | Typical enterprise $ | Why we price at/above |
|------|---------------------|------------------------|
| Portkey Enterprise | ~$100K/yr (AWS MP) | We add ledger + reconciler + anchor |
| LiteLLM Enterprise | Custom $50K–$200K+ | Runtime enforcement, not keys-only |
| Okta IGA (15K users) | $1.26M–$2.52M/yr | We price **per control plane**, not per seat |
| Zscaler + DLP | $250K–$1M+ | Complement — mesh + crystal, not replacement |
| BlackLine | $200K–$1M+/yr | Pre-execution wedge vs close management |
| ValidMind / MRM | $150K–$500K+ | Runtime reserve-before-score |

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
make cg-security-demo       # Cyber Governor
make posture-reconcile-demo # PostureReconcile wedge
make content-guard-demo     # ContentGuard wedge
make algofreeze-demo        # Finance wedge
make wirematch-demo         # Finance wedge
make demo-all-platforms     # Full MG SKU story
```

Related: [HONEST-SCOPE.md](HONEST-SCOPE.md) · [plug-and-play.md](../plug-and-play.md) · [cyber-governor/PLUG-AND-PLAY.md](../../cyber-governor/PLUG-AND-PLAY.md) · [competitive-landscape.md](../finance-governor/competitive-landscape.md)
