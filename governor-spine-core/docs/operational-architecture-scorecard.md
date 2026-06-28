# Operational Architecture Scorecard

**Principle:** In professional software engineering, **maturity is defined by implementation, not intent.** An architecture concept can be brilliant on paper; this document scores what the repository **actually ships** against enterprise engineering benchmarks.

**Assessment basis:** PR #51–#53 (CG consolidation, spine-core, port fixes), ModelGovernor reliability fixes, four-governor 4-tier CI on `main`.

---

## Scorecard (implementation state)

```
[ IDEAL GOLD STANDARD ] ══════════════════════════════════════════► 10/10

[ YOUR REPOSITORY IMPLEMENTATION STATE ]
• Core Transaction Kernel (institutional spine) ──► 8.5/10  Highly robust logical design
• ModelGovernor AI Spend Platform              ──► 7.0/10  Functional demo-gold suite
• Finance / Cyber / Insurance Wedges           ──► 6.0/10  Thin integration scaffolds
• Combined Portfolio Readiness                 ──► 6.5/10  Credible source-code asset
```

| Layer | Score | What earns it | What caps the score |
|-------|-------|---------------|---------------------|
| **Core transactional kernel** | **8.5/10** | Crystallize→seal→commit, hash chains, mesh 409, reserve-before-dispatch, 4-tier CI, chaos, `verify-chain` | Four forked spines; `governor-spine-core` is contract-only |
| **ModelGovernor** | **7.0/10** | `make demo-gold`, reconciler HA, property/chaos tests, Helm overlays | No formal ECP manifest; `make plug` MG step is subset-only |
| **FG / CG / IG wedges** | **6.0/10** | AlgoFreeze, WireMatch, EgressGovern, ClaimGate demo-ready | SubledgerSync, CreditGovern, thin CG wedges = connector SOW |
| **Portfolio total** | **6.5/10** | Pre-hardened IP, honest attestation, acquirer-grade kernel | Not a staffed enterprise vendor |

**Verdict:** Highly capable **source-code asset** and **control-plane scaffold** — not a completed corporate software business.

---

## Three gaps vs true industry gold standard

### 1. Institutional Self-Check vs third-party audits

| Gold standard (10/10) | This repository |
|----------------------|-----------------|
| SOC 2 Type II, ISO 27001, NHS DTAC, etc. from **accredited independent auditors** | **`make plug`** → “Institutional Self-Check Certified” — localized internal validation |
| Signed auditor opinion in data room | Self-generated JSON attestation (`fg_certification_report.py`, examiner packs) |

**Professional framing:** Transparent and correct for an independent developer. Proves code passes **your** gates without claiming unverified regulatory clearances.

**Do not say:** “SOC2 certified,” “examiner approved,” “Industry Leading” without external evidence.

---

### 2. Full systems vs integration scaffolds

| Gold standard (10/10) | This repository |
|----------------------|-----------------|
| Production Grafana dashboards, paging on-call, global DB replication, high-throughput logging pipelines **operated by vendor** | Prometheus rules + Helm CronJob **templates**; buyer operates stack |
| Turnkey ERP/PAS/SIEM replacement | **Integration scaffolds:** clean APIs + facet schemas + tests; **buyer SOW** for live connectors |

**Solid foundations:** MG proxy/reserve path, CG egress + mesh, FG AlgoFreeze/WireMatch demos.

**Scaffolds (honest label):** FG SubledgerSync, AssetLedger, CreditGovern; CG ThreatProxy, IRGate, ComplianceLogger; IG FNOL adapters (webhook **shape normalizers**, not live Guidewire).

---

### 3. Solo developer codebase vs enterprise operational infrastructure

| Gold standard (10/10) | This repository |
|----------------------|-----------------|
| 24×7 global support, 15-minute SLA, cyber liability insurance | Architecture + runbooks; **no support org** |
| Deployed in retail bank payment paths or NHS patient pipelines **as vendor** | Deployable **by buyer engineering** with wiring |

**Professional framing:** Robust **architectural layout** for technical acquirers — not mission-critical vendor-of-record without a company behind it.

---

## Exit positioning (where the asset has highest value)

```
[ THE FANTASY PATH ]
  Pitch “L5 12-SKU Enterprise Platform” as turnkey vendor
       │
       ▼
  Blocked by procurement, SOC2 requests, reference customers, support SLAs

[ THE REALISTIC EXIT ]
  Pitch “Pre-Hardened Source-Code IP Sale” — transactional kernel + 4 governors
       │
       ▼
  Sells to technical founders, RegTech builders, strategic acquirer engineering teams
```

| Buyer type | Pitch | Proof bundle |
|------------|-------|--------------|
| **Technical founder / acqui-hire** | Fork kernel, ship one wedge | `make plug`, L4 CI links, `governor-spine-core` |
| **Strategic acquirer (engineering)** | Control-plane IP vs 18-month build | Scorecard + chaos CI + hash-chain tests |
| **Enterprise procurement (vendor-of-record)** | ❌ Wrong motion unless partner brings ops + audit | — |

See [valuation-pre-revenue.md](../../docs/sales-sheets/valuation-pre-revenue.md) for asset-sale framing.

---

## Mapping scores to certification labels

| Score band | Label | Meaning |
|------------|-------|---------|
| 8–9 | **Kernel architecture — industry-leading class** | Design + CI prove the primitive |
| 6–7 | **L4 Gold / demo-ready** | Per-governor test pyramid + Helm |
| 5–6 | **Integration scaffold** | API + schema; production = SOW |
| — | **L5 Institutional Self-Check** | `make plug` — internal only |
| — | **Industry Leading Gold Standard (product)** | Requires third-party audit + live reference — **not auto-granted** |

Full ladder: [maturity-ladder.md](maturity-ladder.md)

**Path to 9/10:** [roadmap-to-industry-leading-9.md](roadmap-to-industry-leading-9.md)

---

## Verification (objective, reproducible)

```bash
make plug                         # institutional self-check (not SOC2)
make cg-certification-l4-ci       # CG L4
make fg-certification-l4-ci       # FG L4
# IG: make ig-certification-l4-ci
make demo-gold                    # MG 7.0/10 proof path
```

---

## Related

- [transactional-kernel-strategy.md](transactional-kernel-strategy.md) — tech edge + buyer fit
- [maturity-ladder.md](maturity-ladder.md) — L4 / L5 / IL definitions
- [GOVERNOR-PORTFOLIO.md](../../docs/sales-sheets/GOVERNOR-PORTFOLIO.md) — SKU honesty

**Supersedes** removed unaudited self-grades (`architecture-scalability-rating.md` 92/100, `institutional-hardening-forensic-audit.md` 91/100). Evidence index: [forensic-audit-evidence.md](forensic-audit-evidence.md).
