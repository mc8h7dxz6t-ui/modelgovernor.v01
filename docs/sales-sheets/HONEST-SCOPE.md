# Honest product scope — what is actually shipped

**Use this document first** in diligence, investor calls, and exit data rooms.  
It replaces the fiction of “twelve production-hardened enterprise products.”

**As-of:** ModelGovernor + Finance Governor + Cybersecurity Governor on `main`.  
Insurance Governor ships on branch `cursor/insurance-governor-spine-254e` (not merged).

---

## One-sentence truth

**One governance spine pattern** (crystallize → refuse/hold/strand → commit → prove), implemented **three times** (MG / FG / CG), with **a small set of real wedges** at different readiness tiers — not twelve independent product companies.

---

## Readiness tiers (definitions)

| Tier | Label | Meaning | Sell? |
|------|-------|---------|-------|
| **L4** | Shipped | FastAPI platform service + spine integration + automated tests + Postgres CI path + runbook | ✅ Pilot / production with wiring |
| **L3** | Pilot-ready | Spine + K8s/Helm overlays + demo + integration tests; may lack buyer UI | ✅ Paid pilot |
| **L2** | Demo-ready | Scripted demo + unit/schema tests; not full HA story | ✅ Design partner / workshop only |
| **L1** | Spec / scaffold | Schema, spec, partial tests; no standalone production claim | ❌ Not standalone SKU |
| **L0** | Delisted | Do not sell or show in portfolio decks | ❌ |

**Database truth:** **SQLite = local/unit tests only.** Production and vigorous integration tests use **PostgreSQL** (`docs/plug-and-play.md`, `tests/integration/test_postgres_vigorous.py`). Do not describe SQLite as the institutional datastore.

**Demo truth:** `make demo-*` scripts orchestrate **real services in Docker** (gateway, sidecar, reconciler, Postgres). They use **mock providers/feeds**, not production hospital/ad/bank integrations.

---

## What we sell (canonical list)

### Spines (3) — shared IP, not “three unrelated apps”

| Code | Tier | Tests (approx.) | Proof |
|------|------|-----------------|-------|
| `MG-SPINE` | L3–L4 | 120+ MG integration/unit | `make demo-gold`, `make proof-test`, Postgres CI |
| `FG-SPINE` | L3 | 55+ FG | `make fg-demo-gold`, `make fg-spine-test` |
| `CG-SPINE` | L4 | 69+ CG + chaos | `make cg-security-demo`, `make cg-spine-test` |

### ModelGovernor deployment modes (4) — **one product**, four packaging SKUs

| Code | Tier | What it is |
|------|------|------------|
| `MG-PLATFORM-DEMO` | L2 | Mode A Docker demo (`make demo-gold`) |
| `MG-PLATFORM-STAGING` | L3 | K8s staging overlay + ESO |
| `MG-PLATFORM-PRODUCTION` | L3 | Production overlay (Postgres, Sentinel, S3 anchor, OIDC) |
| `MG-ADDON-ENTERPRISE-SECURITY` | L3 | Istio mTLS + LLM egress templates |

### Finance wedges (5)

| Code | Tier | Proof |
|------|------|-------|
| `FG-ALGOFREEZE` | L2 | `make algofreeze-demo`, `test_algofreeze.py` |
| `FG-WIREMATCH` | L2 | `make wirematch-demo`, `test_wirematch.py` |
| `FG-SUBLEDGERSYNC` | L1 | Schema + `test_subledger.py` — design partner |
| `FG-ASSETLEDGER` | L1 | Schema + `test_asset_ledger.py` — design partner |
| `FG-CREDITGOVERN` | L1 | Schema + `test_credit_govern.py` — design partner |

### Cyber wedges (6) — **all L4 shipped**

| Code | Service | Proof |
|------|---------|-------|
| `CG-IDENTITYGATE` | `platforms/identity_gate/` | `test_identity_gate.py` |
| `CG-EGRESSLOCK` | `platforms/egress_lock/` | `test_egress_lock.py` |
| `CG-WITNESSBRIDGE` | `platforms/witness_bridge/` | `test_witness_bridge.py` |
| `CG-LINEAGEINGEST` | `platforms/lineage_ingest/` | `test_lineage_ingest.py` |
| `CG-POSTURERECONCILE` | `platforms/posture_reconcile/` | `test_posture_reconcile.py` |
| `CG-CONTENTGUARD` | `platforms/content_guard/` | `test_content_guard.py` |

**Count:** 3 spines + 4 MG deployment SKUs + 5 FG wedges + 6 CG wedges = **18 codes**, but only **~11 are L2+ sellable today** (3 spines + 4 MG modes + 2 FG demos + 6 CG — with overlap because MG modes are packaging not separate engines).

---

## What we do **not** sell as standalone products

These were listed in the extended catalog / concern matrix. They are **not** separate production-hardened SKUs.

| Former label | Status | Why |
|--------------|--------|-----|
| Compliance Logger / Audit Seal | **L1** | Verify API is part of **spine**; not a standalone logger product |
| Proxy-Risk (Z-score on corp WAN) | **L0** | Not built; mispositioning of AlgoFreeze/MG |
| `MG-ALTDATA` | **L1** | Demo feed only; production = mapping SOW |
| `MG-AIKIT` | **L2** | Stub/trace; subset of MG spine |
| `MG-WEBHOOK-MESH` | **L0** | Not sold standalone; partner Svix/Hookdeck for relay |
| `MG-ADGUARD` | **L0** | Delisted — autonomous ad kill liability |
| `MG-HEALTH` | **L0** | Delisted — no DTAC/FDA/PHI SaaS path |
| `MG-DRIFTGATE` | **L2** | Feature of **MG-SPINE** (demo step 10), not separate product |
| `MG-SPENDGUARD` | **L2** | Same engine as **MG-SPINE** reserve/settle |
| Agent Ledger / Webhook Replay | **L1** | Roadmap patterns; not standalone SKU |

---

## Known non-goals (not “coming soon” hidden features)

| Non-goal | Implication |
|----------|-------------|
| **Hosted multi-tenant SaaS** | Buyer VPC / K8s deploy |
| **SOC 2 Type II** | Not certified; buyer security review required |
| **Compliance auditor UI** | APIs + metrics + verify endpoints; Grafana/Splunk export; pilot UI TBD |
| **Hospital DTAC / FDA clearance** | Health SKU delisted |
| **Replacing QLDB / Splunk / LiteLLM** | Complement — commit-time enforcement layer |

---

## How to pitch without overselling

| Audience | Lead with | Do not lead with |
|----------|-----------|------------------|
| **Buyer (pilot)** | One wedge: WireMatch, AlgoFreeze, or one CG gate | “12 SKUs” or “quad platform” |
| **Investor / acquirer** | Spine IP + test pyramid + 6 CG + 2 FG demos | List ACV as if revenue |
| **Skeptic / engineer** | `HONEST-SCOPE.md` + Postgres test run | Demo script duration |
| **Regulated health** | Nothing until DTAC path exists | MG-HEALTH |

---

## Diligence answers (copy-ready)

**“Twelve production products?”**  
→ No. **One spine pattern**, three governors, **six shipped cyber wedges**, **two finance demo wedges**, MG reserve/settle core. Extended catalog items are **delisted or folded into spine**.

**“SQLite for institutional?”**  
→ **Tests only.** Production path is **Postgres + Redis + K8s**.

**“BEGIN IMMEDIATE on live financial path?”**  
→ **Not used** in this repository. Reserve/settle uses **Postgres atomic updates**; see `sidecar/app/ledger.py` and `test_postgres_vigorous.py`.

**“Show business logic?”**  
→ `sidecar/app/ledger.py`, `ledger_seal.py`, `cyber-governor/tests/test_mesh_block.py`, `finance-governor/tests/test_wirematch.py`.

---

## Related

- [GOVERNOR-PORTFOLIO.md](GOVERNOR-PORTFOLIO.md) — competitive copy (aligned to this scope)
- [plug-and-play.md](../plug-and-play.md) — Mode A/B/C deploy
- [valuation-pre-revenue.md](valuation-pre-revenue.md) — asset worth methodology
