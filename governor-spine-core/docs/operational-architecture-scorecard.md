# Operational Architecture Scorecard

**Principle:** In professional software engineering, **maturity is defined by implementation, not intent.** An architecture concept can be brilliant on paper; this document scores what the repository **actually ships** against enterprise engineering benchmarks.

**Assessment basis:** Wave 0–3 + Wave 1 re-ship on `main` — four-governor L4 CI, `make plug`, live compose-smoke + pilot attestation CI (CG/MG/FG/IG), K1 `ledger_registry`, K2 `portfolio_self_check.json`.

---

## Scorecard (implementation state)

```
[ IDEAL GOLD STANDARD ] ══════════════════════════════════════════► 10/10

[ YOUR REPOSITORY IMPLEMENTATION STATE ]
• Core Transaction Kernel (institutional spine) ──► 8.5/10  Highly robust logical design
• ModelGovernor AI Spend Platform              ──► 7.5/10  demo-gold + compose-smoke CI
• Cybersecurity Governor                       ──► 8.5/10  L4 + live pilot attestation CI
• Finance Governor                             ──► 7.0/10  L4 + pilot attestation CI
• Insurance Governor                           ──► 8.0/10  ClaimGate hero + FNOL/FedNow sandbox CI
• Combined Portfolio Readiness                 ──► 7.5/10  Credible source-code asset
```

| Layer | Score | What earns it | What caps the score |
|-------|-------|---------------|---------------------|
| **Core transactional kernel** | **9.0/10** | K1–K4, H1, **M1 shared spine modules** (checkpoint, mesh, metadata) | Phase C external evidence per governor |
| **ModelGovernor** | **7.5/10** | `make demo-gold`, `compose-smoke-mg`, `mg-pilot-attestation` in CI, reconciler HA | No Phase C design-partner letter |
| **Cybersecurity Governor** | **8.5/10** | L4 CI, `compose-smoke-cg` → `cg-pilot-attestation` in CI, mesh 409 demo | Thin wedges stay 6.0; no Phase C |
| **Finance Governor** | **7.0/10** | L4 CI, AlgoFreeze + WireMatch demos, `fg-pilot-attestation` in CI | SubledgerSync, CreditGovern = connector SOW |
| **Insurance Governor** | **8.0/10** | ClaimGate hero, FNOL/FedNow sandbox CI, SpatialTwin/SubrogationGraph **7.5** mock envelopes | IL 9/10 needs Phase C carrier letter |
| **Portfolio total** | **7.5/10** | Pre-hardened IP, honest attestation, live CI on all four governors | Not IL 9/10 — no governor has Phase C |

**Verdict:** Highly capable **source-code asset** and **control-plane scaffold** — not a completed corporate software business.

---

## IL rubric status (per governor)

| Governor | Code score | IL rubric (5 rows) | Gap to 9/10 |
|----------|------------|-------------------|-------------|
| **Kernel** | 9.0 | K1–K4, H1, M1 | Phase C per governor |
| **MG** | 7.5 | **3/5** | Phase C FinOps design-partner |
| **CG** | 8.5 | **4/5** | Phase C CISO letter |
| **FG** | 7.0 | **3/5** | Phase C treasurer/CRO letter |
| **IG** | 8.0 | **4/5** | Phase C carrier design-partner |
| **Portfolio** | 7.5 | Not IL | No governor has row 5 |

**Do not say:** “Industry Leading platform” or “SOC2 certified” without Phase C external evidence per [maturity-ladder.md](maturity-ladder.md).

---

## Three gaps vs true industry gold standard

### 1. Institutional Self-Check vs third-party audits

| Gold standard (10/10) | This repository |
|----------------------|-----------------|
| SOC 2 Type II, ISO 27001, NHS DTAC, etc. from **accredited independent auditors** | **`make plug`** → “Institutional Self-Check Certified” — localized internal validation |
| Signed auditor opinion in data room | Self-generated JSON attestation (`fg_certification_report.py`, examiner packs) |

**Professional framing:** Transparent and correct for an independent developer. Proves code passes **your** gates without claiming unverified regulatory clearances.

---

### 2. Full systems vs integration scaffolds

| Gold standard (10/10) | This repository |
|----------------------|-----------------|
| Production Grafana dashboards, paging on-call, global DB replication, high-throughput logging pipelines **operated by vendor** | Prometheus rules + Helm CronJob **templates**; buyer operates stack |
| Turnkey ERP/PAS/SIEM replacement | **Integration scaffolds:** clean APIs + facet schemas + tests; **buyer SOW** for live connectors |

**Solid foundations:** MG proxy/reserve path, CG egress + mesh, FG AlgoFreeze/WireMatch demos, IG ClaimGate + FNOL sandbox.

**Scaffolds (honest label):** FG SubledgerSync, AssetLedger, CreditGovern; CG ThreatProxy, IRGate, ComplianceLogger; IG production LiDAR/desk APIs.

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
| **Strategic acquirer (engineering)** | Control-plane IP vs 18-month build | Scorecard + chaos CI + hash-chain tests + live attestation CI |
| **Enterprise procurement (vendor-of-record)** | ❌ Wrong motion unless partner brings ops + audit | — |

Technical proof: [GOVERNOR-PORTFOLIO.md](../../docs/sales-sheets/GOVERNOR-PORTFOLIO.md) · [forensic-audit-evidence.md](forensic-audit-evidence.md)

---

## Mapping scores to certification labels

| Score band | Label | Meaning |
|------------|-------|---------|
| 8–9 | **Kernel architecture — industry-leading class** | Design + CI prove the primitive |
| 6–7 | **L4 Gold / demo-ready** | Per-governor test pyramid + Helm |
| 5–6 | **Integration scaffold** | API + schema; production = SOW |
| — | **L5 Institutional Self-Check** | `make plug` — internal only |
| — | **Industry Leading Gold Standard (product)** | Requires Phase C external evidence — **not auto-granted** |

Full ladder: [maturity-ladder.md](maturity-ladder.md)

**Path to 9/10:** [roadmap-to-industry-leading-9.md](roadmap-to-industry-leading-9.md)

---

## Verification (objective, reproducible)

```bash
make plug && test -f artifacts/portfolio_self_check.json
PYTHONPATH=governor-spine-core python3 -m pytest governor-spine-core/tests/test_sweep_seal.py governor-spine-core/tests/test_ledger_conformance.py -q
make compose-smoke-cg && ATTESTATION_CI=1 make cg-pilot-attestation
make compose-smoke-mg && ATTESTATION_CI=1 make mg-pilot-attestation
make compose-smoke-fg && ATTESTATION_CI=1 make fg-pilot-attestation
make compose-smoke-ig && ATTESTATION_CI=1 make ig-pilot-attestation
make cg-certification-l4-ci
make fg-certification-l4-ci
make ig-certification-l4-ci
make demo-gold
```

---

## Related

- [transactional-kernel-strategy.md](transactional-kernel-strategy.md) — tech edge + buyer fit
- [maturity-ladder.md](maturity-ladder.md) — L4 / L5 / IL definitions
- [GOVERNOR-PORTFOLIO.md](../../docs/sales-sheets/GOVERNOR-PORTFOLIO.md) — SKU honesty

**Supersedes** removed unaudited self-grades (`architecture-scalability-rating.md` 92/100, `institutional-hardening-forensic-audit.md` 91/100). Evidence index: [forensic-audit-evidence.md](forensic-audit-evidence.md).
