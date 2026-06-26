# Business model — explicit claims for external critique

**Purpose:** Give another AI (or human) a **falsifiable** picture of what exists, what is sellable, and how money is supposed to flow. Attack this document; do not attack a imaginary twelve-SKU empire.

**Repo:** `modelgovernor.v01` on `main` as of 2026-06.  
**Companion truth doc:** [HONEST-SCOPE.md](HONEST-SCOPE.md)  
**Critique instruction:** Flag any claim below that is not evidenced by code, tests, or cited paths.

---

## 1. What we are (one paragraph)

We built a **repeatable control-plane pattern** for **irreversible commits**: snapshot policy/context (**crystallize**), return **allow / hold / strand / reject**, then **commit** with an **append-only hash chain** and optional **S3 anchor**. The pattern is implemented **three times**:

| Governor | Domain | Protocol name |
|----------|--------|---------------|
| **ModelGovernor (MG)** | LLM / agent **spend dispatch** | Reserve → settle ledger |
| **Finance Governor (FG)** | Treasury / algo **financial commits** | Crystal Commit Protocol (CCP) |
| **Cybersecurity Governor (CG)** | Security **authorize / egress** | Threat Crystal Protocol (TCP) |

We are **not** a hosted SaaS, **not** SOC 2 certified, **not** on NHS/CCS frameworks, and **not** twelve independent enterprise products.

**Insurance Governor (IG):** 11 platforms + L4 packaging on branch `cursor/insurance-governor-spine-254e` — **not merged to `main`**. Do not count IG in `main`-branch revenue claims.

---

## 2. What we have legitimately built (evidence-backed)

### 2.1 Shared engineering (real, not mock scripts)

| Asset | Evidence | Approx. scale |
|-------|----------|---------------|
| MG spine (gateway / sidecar / reconciler) | `sidecar/`, `gateway/`, `reconciler/`, `migrations/` | `ledger.py` ~995 LOC; 120+ MG integration/unit tests |
| FG spine | `finance-governor/spine/` | 55+ FG tests; `make fg-spine-test` |
| CG spine | `cyber-governor/spine/` | ~6,900 LOC under `cyber-governor/`; 69+ CG tests |
| Postgres production path | `docs/plug-and-play.md`, `tests/integration/test_postgres_vigorous.py` | CI Tier 2 on Postgres 16 |
| SQLite | Unit/fast tier only | CI Tier 1 — **not sold as prod DB** |
| Hash chain verify | `sidecar/app/ledger_seal.py`, `GET /internal/.../verify-chain` | Integration tests |
| HA patterns | Leader-elected reconciler, `FOR UPDATE SKIP LOCKED` sweeps | `reconciler/app/sweeper.py`, Postgres tests |
| Deploy artifacts | K8s overlays, Helm charts | `deploy/overlays/`, `cyber-governor/deploy/`, CI manifest render |
| Chaos / property tests | Toxiproxy, Hypothesis chain properties | CG/FG CI tiers |

**Demos:** `make demo-gold`, `make cg-security-demo`, `make algofreeze-demo` orchestrate **Docker Compose stacks** (Postgres + real FastAPI services). They use **mock providers/feeds**, not fake `print()` success.

**Does not exist in repo:** `inst_spine`, `BEGIN IMMEDIATE` on financial path, standalone “compliance logger” product.

### 2.2 Product surfaces (by governor)

#### Cybersecurity Governor — **strongest build**

| Code | Service path | CI tests | Demo |
|------|--------------|----------|------|
| `CG-IDENTITYGATE` | `platforms/identity_gate/` | `test_identity_gate.py` | `cg-security-demo` |
| `CG-EGRESSLOCK` | `platforms/egress_lock/` | `test_egress_lock.py` | same |
| `CG-WITNESSBRIDGE` | `platforms/witness_bridge/` | `test_witness_bridge.py` | witness path in demo |
| `CG-LINEAGEINGEST` | `platforms/lineage_ingest/` | `test_lineage_ingest.py` | lineage demo |
| `CG-POSTURERECONCILE` | `platforms/posture_reconcile/` | `test_posture_reconcile.py` | `posture-reconcile-demo` |
| `CG-CONTENTGUARD` | `platforms/content_guard/` | `test_content_guard.py` | `content-guard-demo` |

**Differentiator:** Threat **Mesh** — e.g. STRANDED identity blocks egress commit (`cyber-governor/tests/test_mesh_block.py`).

#### Finance Governor

| Code | Status | Evidence |
|------|--------|----------|
| `FG-SPINE` | Pilot-ready (L3) | Spine + CCP docs + Postgres tests |
| `FG-ALGOFREEZE` | Demo-ready (L2) | `platforms/algofreeze/`, `test_algofreeze.py` |
| `FG-WIREMATCH` | Demo-ready (L2) | `platforms/wire_match/`, `test_wirematch.py` |
| `FG-SUBLEDGERSYNC` | Spec/scaffold (L1) | Schema + `test_subledger.py` — **not standalone sale** |
| `FG-ASSETLEDGER` | Spec/scaffold (L1) | `test_asset_ledger.py` |
| `FG-CREDITGOVERN` | Spec/scaffold (L1) | `test_credit_govern.py` |

#### ModelGovernor

| Code | Status | Evidence |
|------|--------|----------|
| `MG-SPINE` | Pilot-ready (L3) | Reserve/settle, drift lockout, reconciler |
| `MG-PLATFORM-DEMO` | Demo (L2) | `make demo-gold` |
| `MG-PLATFORM-STAGING/PRODUCTION/SECURITY` | Packaging (L3) | K8s/Helm manifests — **not four engines** |

**Delisted (L0):** `MG-HEALTH`, `MG-ADGUARD`, standalone `MG-WEBHOOK-MESH` — do not sell.

---

## 3. Readiness matrix — “ready” vs “almost ready” vs “not sellable”

| Tier | Meaning | Sell motion | Scale motion |
|------|---------|-------------|--------------|
| **Ready to sell (pilot)** | L2+ code + demo + tests; buyer VPC deploy | **£15–40K / $20–50K** fixed pilot, 4–8 weeks | N/A |
| **Almost ready (scale)** | L3 spine + K8s + Postgres CI; missing SOC2/UI/24×7 | Needs **first pilot logo** + SI partner | After 3–5 pilots or acquirer |
| **Not sellable standalone** | L0–L1 | Do not pitch | — |

### Ready to sell **now** (paid pilot)

| Offer | Includes | Buyer |
|-------|----------|-------|
| **Cyber commit pack** | IdentityGate + EgressLock + mesh + spine in buyer VPC | Mid-market SaaS, insurtech MDR, security-conscious platform |
| **Wire gate** | WireMatch + FG spine wiring | Fintech treasury, payment infra |
| **Algo freeze** | AlgoFreeze wedge | Prop/systematic shop, algo desk |
| **LLM spend gate** | MG reserve/settle + shadow mode | Team with 3–5 agents or internal LLM gateway |

### Almost ready (needs one pilot to unlock “scale” narrative)

| Offer | Gap to close |
|-------|----------------|
| **MG production SKU** | SOC2, support runbook, optional admin UI |
| **FG CreditGovern / Subledger** | Design partner to finish integration |
| **Full tri-governor bundle** | Not a GTM — acquirer-only story |
| **Insurance Governor** | Merge to `main` + one claims LOI |

### Not sellable (explicit)

- NHS clinical / DTAC path  
- Tier-1 bank live payment rail with our SLA  
- Softcat/Bytes/CCS framework SKU without acquirer balance sheet  
- Six-figure ACV **as first contract** without certification team  

---

## 4. Business model (three tracks — pick one)

### Track A — **IP / strategic sale** (primary for asset-heavy, team-light)

| Element | Claim |
|---------|-------|
| **Customer** | Platform co with frameworks + insurance (Coalition, Palo Alto, Socotra/Earnix rollup, ServiceNow) |
| **Product** | Non-exclusive license + repo transfer of spine + CG (+ FG/MG as bundle) |
| **Price** | **$2.5M–$5M** fast close · **$8M–$12M** with competitive process (pre-revenue IP, not ARR) |
| **Why they buy** | Commit-time enforcement + mesh + tests — faster than 18-month internal build |
| **Scale** | Buyer’s salesforce — **not ours** |

### Track B — **Direct paid pilot** (primary for market proof)

| Element | Claim |
|---------|-------|
| **Customer** | 50–500 employee fintech, insurtech, security SaaS — **not** tier-1 bank/NHS |
| **Product** | **One wedge** in buyer VPC (Postgres, K8s or Compose) |
| **Price** | **$20K–$50K** fixed fee, 4–8 weeks |
| **Delivery** | Shadow mode → enforce on one commit path; buyer owns prod ops |
| **Success** | Signed case study → raises ACV ceiling toward **$80K–$150K** yr-2 |

### Track C — **Scale-up vendor** (not available today)

| Requirement | Status |
|-------------|--------|
| SOC 2 Type II | ❌ |
| 24×7 Sev-1 | ❌ |
| Auditor/compliance UI | ❌ |
| $5M+ PI/cyber insurance | ❌ |
| Reseller (Softcat/Bytes) listing | ❌ |
| 10+ engineers | ❌ |

**Critique target:** Track C is **aspirational**; claiming we operate Track C today is **false**.

---

## 5. Market equivalents (what we are / are not)

### 5.1 By governor

#### Cyber (CG)

| We are closest to | What they do | What we do **different** | What they do **better** |
|-------------------|--------------|--------------------------|-------------------------|
| **Okta** (session/IGA) | Identity lifecycle | **Commit-time** session arm + STRAND on hijack | Seat scale, IdP ecosystem |
| **Zscaler** (DLP/egress) | Network egress policy | **Mesh-aware** egress commit + crystal proof | Global edge, CASB scale |
| **Wiz / Prisma** (CNAPP) | Posture alerts | **PostureReconcile** at authorize-time STRAND | Agentless cloud coverage |
| **Splunk / SIEM** | Correlate alerts | **Deterministic refuse** before commit | Analytics, SOAR ecosystem |
| **Palo Alto Prisma AIRS** | AI + security platform | **TCP + mesh** on authorize path | Brand, distribution, Portkey bundle |

**Position:** **Inline governance wedge** — complement, not replace SIEM/CNAPP.

#### Finance (FG)

| Equivalent | Overlap | Our wedge |
|------------|---------|-----------|
| **ServiceNow GRC / Archer** | Policy register | **Runtime** wire/freeze gate |
| **BlackLine** | Close/reconcile | **Match-at-clear** (Subledger — L1) |
| **ValidMind / ModelOp** | MRM documentation | **Reserve-before-score** (Credit — L1) |
| **Payment hubs (Finastra)** | Own the rail | **Pre-rail** semantic gate (WireMatch) |
| **EMS kill switch** | Blunt halt | **Deploy SHA + feed** crystal (AlgoFreeze) |

#### Model / AI (MG)

| Equivalent | Overlap | Our wedge |
|------------|---------|-----------|
| **LiteLLM Enterprise** | Proxy, keys, budgets | **Reserve → settle** ledger + stranded repair |
| **Portkey** (~$100K/yr) | Gateway, guardrails | Tamper-evident chain + reconciler |
| **Helicone** | Observability | **Pre-dispatch enforcement** |
| **Verdict** (agent policy) | Allow/deny/fix-first on tool calls | **Ledger + HA reconciler** + multi-domain spine |
| **AWS Budgets / cloud alerts** | Post-hoc spend | **Atomic per-trace cap before call** |

**Commoditization risk:** MG is **highest** — LiteLLM/Portkey plugins can copy budget counters.

### 5.2 Pricing equivalents (what market actually pays)

| Comp | Typical buyer pays | Our **honest** stage |
|------|-------------------|----------------------|
| Portkey Enterprise | ~$100K/yr | We are **not** there without pilots |
| LiteLLM Enterprise | $50K–$200K/yr | Same |
| Okta (15K users) | $1.2M–$2.5M/yr | We price **control plane**, not seats — **after** proof |
| Zscaler slice | $250K–$1M/yr | Complement sale |
| **Our pilot** | — | **$20K–$50K** fixed |
| **Our IP exit** | — | **$2.5M–$5M** |

**List ACV in older docs ($120K–$900K)** = **target state post-certification**, not first deal.

---

## 6. Go-to-market (explicit, non-fantasy)

### 6.1 Who we sell to **now**

| Priority | Persona | Wedge |
|----------|---------|-------|
| 1 | VP Eng / platform lead, 50–500 emp | CG Identity + Egress |
| 2 | Head of treasury / payments eng | FG WireMatch |
| 3 | Trading tech / CRO office | FG AlgoFreeze |
| 4 | AI platform lead (agents in staging) | MG shadow → enforce |

### 6.2 Who we do **not** sell to **now**

- NHS trusts (no DTAC)  
- Tier-1 banks (agent/wire production SLA)  
- Via Softcat/Bytes without acquirer  
- “Full tri-governor transformation” RFPs  

### 6.3 Channel

| Channel | Viable? |
|---------|---------|
| **Direct founder outbound** | ✅ |
| **Design partner** | ✅ |
| **Strategic corp dev (IP)** | ✅ |
| **SI subcontract** (Deloitte/KPMG component) | ⚠️ after pilot artifact |
| **Reseller framework** | ❌ today |

---

## 7. Unit economics (honest, pre-revenue)

| Metric | Assumption |
|--------|------------|
| **Pilot COGS** | ~2–4 weeks founder + eng time; buyer VPC |
| **Pilot price** | $25K–$40K |
| **Gross margin** | High if solo; **no support org** |
| **CAC** | Founder sales — low cash, high time |
| **Path to $1M ARR** | ~25–40 pilots **or** 1 acquirer — **not** 10× $120K ACV in year 1 |
| **Path to “scale”** | Acquirer or raise after 3 pilot logos + SOC2 roadmap |

---

## 8. Moat (what is defensible — critique welcome)

| Moat claim | Strength | Weakness |
|------------|----------|----------|
| **Commit-time + hash proof** | Medium — rare as **integrated** spine | QLDB, immutability logs, “good enough” for many buyers |
| **Threat / Crystal Mesh** | Medium-strong for CG | Policy engines (OPA) + SIEM could approximate |
| **Reserve → settle + reconciler** | Medium for MG | LiteLLM adding ledger semantics |
| **CCP on finance commits** | Medium for FG | Banks build internal |
| **Test pyramid + chaos** | Medium — diligence asset | Copyable with time |
| **Brand / distribution** | **None today** | — |

---

## 9. Explicit weaknesses (please attack these)

1. **No revenue, no logos, no SOC 2**  
2. **No compliance UI** — APIs/metrics only  
3. **No 24×7 support** — disqualifies live-rail production claims  
4. **MG commoditization** vs LiteLLM/Portkey  
5. **FG L1 wedges** oversold if pitched as production  
6. **IG not on `main`**  
7. **Single-founder / team-light** — TPRM failure at resellers  
8. **Shadow mode** required for responsible pilot — not weakness, but caps “inline day one” claims  
9. **Historical marketing** claimed 12 SKUs — credibility debt until HONEST-SCOPE is default  

---

## 10. Falsifiable claims for the critiquer

Answer **true / false / partially true** for each:

| # | Claim |
|---|-------|
| 1 | CG has six shipped FastAPI platforms with automated tests on `main`. |
| 2 | Production deploy targets PostgreSQL, not SQLite. |
| 3 | The company can legitimately invoice $120K ACV to a hospital today. |
| 4 | Softcat will list this vendor without audited accounts and insurance. |
| 5 | MG reserve/settle is technically distinct from LiteLLM budget middleware. |
| 6 | WireMatch is production-ready on a live SWIFT connection without integration SOW. |
| 7 | This is twelve independent production-hardened products. |
| 8 | Track A (IP sale $2.5M–$5M) is more realistic than Track C (scale vendor) today. |
| 9 | Cyber is the strongest sellable governor on `main`. |
| 10 | Demos are pure `print()` scripts with no real services. |

**Expected answers:** 1 T, 2 T, 3 F, 4 F, 5 T (debate degree), 6 F, 7 F, 8 T, 9 T, 10 F.

---

## 11. Summary box (for critique prompt)

```
COMPANY TYPE:     Pre-revenue infrastructure IP + pilot services
NOT:              Hosted SaaS, SIEM, hospital vendor, reseller SKU
BUILT (main):     MG spine, FG spine + 2 demos, CG spine + 6 wedges
TESTS:            ~226+ automated tests, Postgres CI, chaos tier (CG)
SELL NOW:         $20–50K single-wedge VPC pilot OR $2.5–5M IP exit
SELL LATER:       $80–150K ACV (needs SOC2, logos, UI, support)
STRONGEST:        Cyber (IdentityGate + EgressLock + mesh)
WEAKEST GTM:      MG alone vs LiteLLM/Portkey
DELISTED:         Health, ad-tech, webhook mesh, 12-SKU empire story
```

---

## Related documents

- [HONEST-SCOPE.md](HONEST-SCOPE.md) — L0–L4 product tiers  
- [GOVERNOR-PORTFOLIO.md](GOVERNOR-PORTFOLIO.md) — competitive copy (aligned)  
- [valuation-pre-revenue.md](valuation-pre-revenue.md) — IP worth methodology  
- [plug-and-play.md](../plug-and-play.md) — deploy modes  
