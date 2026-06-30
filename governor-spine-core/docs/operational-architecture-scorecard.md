# Operational Architecture Scorecard

**Principle:** In professional software engineering, **maturity is defined by implementation, not intent.** An architecture concept can be brilliant on paper; this document scores what the repository **actually ships** against enterprise engineering benchmarks.

**Assessment basis:** Wave 0–3 + kernel K1–K4/H1/M1 + **IL rubric engine** (`spine_core.il_rubric`) — scores computed from repo evidence, not hand-waved.

---

## Scorecard (implementation state)

```
[ IDEAL GOLD STANDARD ] ══════════════════════════════════════════► 10/10

[ ENGINEERING CEILING — Phase A+B complete, Phase C pending ]
• Core Transaction Kernel                      ──► 9.0/10  K1–K4, H1, M1
• ModelGovernor AI Spend Platform              ──► 8.5/10  4/5 IL rubric rows
• Cybersecurity Governor                       ──► 8.5/10  4/5 IL rubric rows
• Finance Governor                             ──► 8.5/10  AlgoFreeze+WireMatch hero CI
• Insurance Governor                           ──► 8.5/10  ClaimGate + FNOL/FedNow CI
• Combined Portfolio (engineering)             ──► 8.5/10  IL 9/0 blocked on Phase C only
```

| Layer | Engineering | IL claim | What earns engineering 8.5 | Gap to IL 9/10 |
|-------|-------------|----------|---------------------------|----------------|
| **Kernel** | **9.0** | 9.0 code | K1–K4, H1, M1 shared spine | — |
| **ModelGovernor** | **8.5** | 8.5 | L4 + plug + live CI + demo-gold hero | Phase C FinOps design-partner |
| **Cybersecurity Governor** | **8.5** | 8.5 | L4 + live CI + egress wedge attestation | Phase C CISO VPC letter |
| **Finance Governor** | **8.5** | 8.5 | L4 + hero integration tests + compose-smoke wedges | Phase C treasurer/CRO letter |
| **Insurance Governor** | **8.5** | 8.5 | L4 + FNOL/FedNow sandbox + live CI | Phase C carrier letter |
| **Portfolio** | **8.5** | **8.5** | `make plug` + IL rubric evaluation | **Row 5 per governor** |

**Verdict:** Engineering path to **8.5/10 is complete** across the portfolio. **IL 9/10** requires Phase C external evidence only — see [artifacts/reliability/README.md](../../artifacts/reliability/README.md).

---

## IL rubric — five dimensions (path to 9/10)

Computed by `PYTHONPATH=governor-spine-core python3 -c "from spine_core.il_rubric import evaluate_portfolio; ..."` and emitted in `artifacts/portfolio_self_check.json` after `make plug`.

| # | Row | Maps to |
|---|-----|---------|
| 1 | L4 engineering | **Robustness** — `*-certification-l4-ci` |
| 2 | L5 self-check | **Execution** — `make plug` |
| 3 | Live stack proof | **Reliability** — compose-smoke + pilot attestation in CI |
| 4 | Hero wedge depth | **Architecture** — demo + attestation probes |
| 5 | Phase C evidence | **Code/external** — `cluster_attestation.json` validated |

| Governor | Rows green | Engineering | Dimensions (arch/code/exec/robust/reliable) | Phase C blocker |
|----------|------------|-------------|---------------------------------------------|-----------------|
| **MG** | **4/5** | 8.5 | 9 / 7 / 9 / 9 / 9 | FinOps design-partner VPC |
| **CG** | **4/5** | 8.5 | 9 / 7 / 9 / 9 / 9 | CISO VPC letter |
| **FG** | **4/5** | 8.5 | 9 / 7 / 9 / 9 / 9 | Treasurer/CRO letter |
| **IG** | **4/5** | 8.5 | 9 / 7 / 9 / 9 / 9 | Carrier design-partner |
| **Portfolio** | — | **8.5** | min(kernel, governors) | All four row-5 artifacts |

**Do not say:** “Industry Leading 9/10” or “SOC2 certified” until Phase C validates per governor.

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
