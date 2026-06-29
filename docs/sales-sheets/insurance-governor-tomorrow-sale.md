# Insurance Governor — Spec Sales Sheet (Asset Sale)

**SKU:** `IG-PLATFORM-PRODUCTION`  
**As-of:** June 2026 · L4 Gold certified · 83 tests · data room published (7/7 probes)  
**Tagline:** Loss-control attestation spine — prove policy warranties at runtime, not after the claim.

---

## Executive summary (60 seconds)

Insurance Governor is a **governed commit control plane** for insurers and MGAs. It sits **in front of** indemnity spend, binds, and parametric triggers — not inside your PAS. Every decision crystallizes to a **hash-chained reserve ledger** with examiner-grade `verify-chain` proof.

**You are buying:** 11 deployable platforms + shared spine + warranty mesh + UK/US GTM + data room — packaged for financial-lines loss control (Cyber, D&O, E&O, Crime).

| | |
|---|---|
| **Buyer tomorrow** | Strategic acquirer, InsurTech platform, carrier innovation lab, PE roll-up |
| **List ACV when operated** | **$320K–$850K / year** |
| **Time to pilot** | 4–8 weeks |
| **Demo** | `make ig-full-rehearsal` (Mac + Docker) |

---

## What you get — component by component

### The spine (ports 8100–8102)

| Component | What it does | Why better than competitor |
|-----------|--------------|----------------------------|
| **Gateway** (8100) | Single governed-commit API; routes all platform decisions to the ledger | **vs PAS APIs:** Guidewire/Snapsheet expose workflow APIs — they do not reserve-before-payout with tamper-evident hash chains. Gateway is a **financial control plane**, not a screen flow. |
| **Sidecar** (8101) | Crystallize → commit → reserve mutation; `claim_events` hash chain; `verify-chain` | **vs audit logs:** SIEM and PAS audit tables are mutable or export-based. Sidecar is **append-only with cryptographic row hashes** — 422 on tamper. |
| **Reconciler** (8102) | Horizon sweeps, reserve expiry, diagnostic halt | **vs batch ETL:** Reserve releases are event-sourced on the same chain as commits — no “mystery balance” after quarter close. |
| **Postgres + mesh** | Shared reserve ledgers, payment idempotency, 6 cross-platform warranty rules | **vs point tools:** No incumbent PAS enforces “model frozen → block payout” across products at commit time. |

**Spine alone is infrastructure.** Commercial value unlocks when ≥2 platforms share the mesh.

---

### Loss-control wedges (lead the financial-lines pitch)

| Platform | Port | What it does | Why better than competitor |
|----------|------|--------------|----------------------------|
| **ModelRiskFreeze** | 8111 | Freezes claims/pricing AI on version drift; blocks downstream commits via mesh | **vs MRM spreadsheets / GRC:** Tracks model inventory but does not **stop indemnity** at runtime. **vs Earnix/Federato:** Pricing optimization — no commit gate. ModelRiskFreeze is **AlgoFreeze for insurance** — catastrophic E&O tail reduction. |
| **IndemnityPayGate** | 8110 | Semantic payee verification gate before crime/FI indemnity payment | **vs bank positive pay / AP controls:** Corporate treasury tools are outside the policy warranty story. **vs PAS payment modules:** Pay after adjudication — not governed semantic match on payee identity. WireMatch analogue for **crime deductible reduction**. |
| **UnderwritingGovern** | 8112 | Fair-lending / bias gate per bind; mesh blocks BindAuthority on `VIOLATION` | **vs quarterly fairness reports:** Retrospective. **vs credit bureaus:** Consumer credit — not insurance bind compliance crystal per application. CreditGovern analogue — **D&O / Consumer Duty** defense-cost story. |
| **ReserveReconcile** | 8113 | Case reserve vs reinsurance/subledger match; mesh blocks payout on `DRIFT` | **vs actuarial spreadsheets / BI:** Detect drift at close — not **block payment** when reserves disagree. SubledgerSync analogue — **solvency / D&O misstatement** prevention. |

---

### Claims & specialty wedges

| Platform | Port | What it does | Why better than competitor |
|----------|------|--------------|----------------------------|
| **ClaimGate** | 8103 | Policy rules, deductibles, SIU referral, FNOL webhooks (6 vendors), payment rail, write-back | **vs Guidewire ClaimCenter rules:** Rules run inside PAS — no shared mesh, no hash-chain attestation export. **vs Shift/FRISS:** Fraud **detection** — not governed **payout commit** with idempotent rails. ClaimGate is the **indemnity frequency/severity lever** with FNOL ingest (Guidewire, Snapsheet, Majesco, Acturis, SSP, ICE). |
| **BindAuthority** | 8104 | Premium/limit bind gate; mesh blocks on underwriting violation | **vs PAS authority tables:** Static limits — no cross-platform warranty enforcement at bind commit. |
| **ParametricOracle** | 8105 | Oracle feed + `sha256(source:payload)` attestation before parametric trigger | **vs raw weather APIs / Chainlink read:** Data feed without **governed reserve commit** and examiner hash. Cat/parametric MGAs get **trigger proof**, not just a number. |
| **ZkClaimAudit** | 8106 | SHA-256 fact commitments; selective disclosure proofs for exams | **vs document vaults:** Storage — not **cryptographic commitment** that disclosed subset recomputes same hash. Lloyd's / state DOI exam narrative. |
| **SpatialTwin** | 8107 | LiDAR point-cloud hash + damage estimate gate | **vs photogrammetry vendors:** Estimate output — no **governed commit** tied to reserve. Property/cat spatial wedge (scaffold + tests; vendor connectors phase 2). |
| **BatteryLiability** | 8108 | EV battery SOH / thermal liability gate | **vs telematics dashboards:** Telemetry — no policy warranty enforcement at claim commit. Auto OEM / fleet programs. |
| **SubrogationGraph** | 8109 | Multi-defendant recovery routing gate | **vs subro desk workflow:** Task management — not governed recovery commit on spine. |

---

## The moat competitors cannot copy in 90 days

**Warranty Enforcement Engine** — 6 `crystal_mesh_rules` seeded in production:

| Parent breach | Blocks | Insurance warranty enforced |
|---------------|--------|----------------------------|
| ModelRiskFreeze `FROZEN` | ClaimGate, IndemnityPayGate | No auto-adjudication / payment on wrong model version |
| ClaimGate `REFERRED` | IndemnityPayGate | No payment while SIU open |
| UnderwritingGovern `VIOLATION` | BindAuthority | No bind while fairness breach |
| ReserveReconcile `DRIFT` | ClaimGate, IndemnityPayGate | No payout on reserve mismatch |

**Why incumbents don’t have this:** PAS vendors sell workflow + data model. Fraud vendors sell scores. MRM sells inventory. None ship a **cross-product commit interceptor** with shared reserve semantics and mesh invariants — that is the IP bundle you are buying.

---

## Integrations & production proof (not slideware)

| Surface | Status |
|---------|--------|
| FNOL ingest | Guidewire, Snapsheet, Majesco, Acturis, SSP, ICE |
| FNOL write-back | Guidewire, Acturis, ICE (dry-run / live) |
| Payment rails | ACH stub, FedNow sandbox, FedNow live, clearinghouse adapters |
| Oracle feeds | USGS, NOAA, Chainlink-style with attestation hash |
| Infra | Helm, Istio mTLS, PgBouncer, ArgoCD, S3 Object Lock anchors |
| Certification | L4 Gold — 4-tier CI, load + Toxiproxy chaos |
| Data room | `docs/insurance-governor/data-room/published/` — **7/7 probes**, manifest SHA-256 |

```bash
make ig-full-rehearsal    # Mac + Docker — refresh published artifacts
make ig-demo              # 5-minute room demo
```

---

## Competitive landscape (one table)

| Category | Examples | What they do | What IG does they don’t |
|----------|----------|--------------|-------------------------|
| **PAS / claims** | Guidewire, Duck Creek, Majesco, Acturis | Policy admin, FNOL workflow, reserves UI | Runtime warranty mesh + hash-chained commit control |
| **Claims InsurTech** | Snapsheet, CCC | Digital FNOL, photos, routing | Governed payout gate + attestation export |
| **Fraud / SIU** | Shift, FRISS | Detection scores, referrals | SIU **blocks commit**, not just flags |
| **UW / pricing** | Earnix, Federato | Rate, price, portfolio | Per-bind compliance crystal + mesh block |
| **GRC / MRM** | Archer, MetricStream | Model inventory, policy docs | **Freeze → block indemnity** at runtime |
| **Service mesh** | Istio, Linkerd | mTLS, traffic | Domain semantics: reserves, facets, mesh rules |

**Positioning line:** *“We are not replacing your PAS — we are the loss-control layer your actuaries and CRO can underwrite against.”*

---

## Packaging when operated (not asset sale)

| SKU component | List ACV (annual) |
|---------------|-------------------|
| Spine HA kit (gateway, sidecar, reconciler) | $180K–$400K |
| ClaimGate + FNOL pack (6 adapters + write-back) | $60K–$120K |
| Loss-control wedge (pick one at depth) | $80K–$150K each |
| Specialty wedge (Zk, Oracle, Spatial, etc.) | $40K–$100K each |
| **Full production bundle** | **$320K–$850K** |

---

## Pre-revenue asset valuation — tomorrow sale

*Illustrative ranges for asset purchase / acqui-hire / IP sale conversations. Not a formal appraisal. Methodology: replacement cost (40%) + differentiation premium (35%) + implied commercial value (25%).*

### Insurance Governor standalone (this SKU)

| Lens | Low | Mid | High |
|------|-----|-----|------|
| Replacement cost (11 platforms + spine + 83 tests + Helm/GTM) | $1.2M | $1.6M | $2.0M |
| Differentiation (warranty mesh + hash-chain + L4 CI) | +$400K | +$800K | +$1.2M |
| **Pre-revenue fair value** | **$1.6M** | **$2.4M** | **$3.2M** |

**Recommended ask tomorrow:** **$2.5M–$3.5M**  
**Walk-away floor:** **$1.8M** (replacement cost + minimal premium)  
**Strategic buyer with carrier pipeline:** **$3.5M–$4.5M**

### What moves the number in the room

| Evidence | Valuation impact |
|----------|------------------|
| Published data room (7/7 probes, manifest hashes) | Baseline credibility — included |
| Named design-partner LOI (even unpaid) | +$500K–$1.0M |
| First paid pilot ($150K+) | 3–5× on that logo |
| Full repo bundle (ModelGovernor + Finance Governor + IG) | **$5.0M–$8.5M** consolidated |

### Tomorrow sale structures

| Structure | Typical range | Best for |
|-----------|---------------|----------|
| **IP + repo assignment** | $2.0M–$3.5M | Acquirer with eng team to operate |
| **IP + 90-day transition** | +$200K–$400K services | Buyer needs handoff |
| **Exclusive license (not sale)** | $400K–$800K/yr | Buyer wants optionality |
| **Acqui-hire + asset** | Asset price + team | Strategic with hiring budget |

---

## One-slide proof for tomorrow

1. **Problem:** Policy warranties are enforced *after* the loss — questionnaires, not runtime controls.  
2. **Product:** 11 governed platforms on a hash-chained spine with cross-platform warranty mesh.  
3. **Proof:** L4 Gold CI, 7/7 attestation probes, published data room, FNOL adapters live.  
4. **Moat:** Mesh rules block cascading losses (model freeze → payout block) — PAS cannot do this without rebuilding commit semantics.  
5. **Ask:** **$2.5M–$3.5M** pre-revenue asset · **$320K–$850K** ACV when operated.

---

## Data room & demo paths

| Asset | Path |
|-------|------|
| This sheet | `docs/sales-sheets/insurance-governor-tomorrow-sale.md` |
| Full production spec | `docs/sales-sheets/insurance-governor-production.md` |
| Published attestation | `docs/insurance-governor/data-room/published/manifest.json` |
| Redacted DD excerpt | `docs/insurance-governor/data-room/design-partner-attestation-redacted.md` |
| Gold standard | `docs/insurance-governor/institutional-gold-standard.md` |
| Live demo | `make ig-demo` → `make ig-pilot-attestation` |

---

*Figures are illustrative list prices and pre-revenue estimates for negotiation support. Buyer should run own technical diligence via `make ig-full-rehearsal` on the `cursor/insurance-governor-spine-254e` branch.*
