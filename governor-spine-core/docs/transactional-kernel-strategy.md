# Transactional Kernel — Technical Edge, Commercial Reality, Buyer Fit

**Classification:** Strategic due-diligence brief  
**Audience:** acquirers, technical founders, design-partner CTOs  
**Portfolio readiness:** **7.5/10** — see [operational-architecture-scorecard.md](operational-architecture-scorecard.md)

---

## Executive verdict

Maturity is **implementation, not intent**. The **core transactional kernel** scores **8.5/10** — industry-leading **class** architecture with CI proof. The **combined portfolio** scores **7.5/10** — a credible **pre-hardened source-code asset** with live attestation CI on all four governors; not IL 9/10 without Phase C.

| Dimension | Score | Evidence |
|-----------|-------|----------|
| **Kernel (institutional spine)** | **8.5/10** | Crystallize→seal→commit, hash chains, mesh 409, 4-tier CI |
| **ModelGovernor** | **7.0/10** | `make demo-gold`, reserve-before-dispatch, chaos |
| **FG / CG / IG wedges** | **6.0/10** | Demo wedges + integration scaffolds |
| **Commercial / ops entity** | **N/A** | No SOC2, no 24×7 support org |

**Realistic exit:** Pre-hardened **IP sale** to technical founders — not fantasy **L5 12-SKU enterprise platform** procurement.

---

## 1. True technical edge (kernel — 8.5/10)

```
STANDARD:  clear → DB → log → dashboard (too late)
GOVERNORS: ingress → crystallize → guardrails/mesh → seal → commit → verify-chain
```

| Primitive | Implementation |
|-----------|----------------|
| Pre-execution fail-closed | HTTP 409 mesh, reserve reject, diagnostic 503 |
| Tamper-evident order | `prev_hash`→`row_hash`; **not** Lamport clocks |
| Durable-before-dispatch | Postgres escrow before provider call (MG) |
| Degradation | `circuit_breaker.py`, `fallback_limiter.py`, `mode_contract.py` |

---

## 2. Three diligence gaps (why not 10/10)

### Self-check vs third-party audit

`make plug` outputs **Institutional Self-Check Certified** — professional and transparent. It is **not** SOC 2 Type II, ISO 27001, or NHS DTAC.

### Scaffolds vs full systems

AlgoFreeze, WireMatch, EgressGovern, ClaimGate = **demo-ready**. SubledgerSync, CreditGovern, thin CG wedges = **connector SOW**.

### Codebase vs operating company

No global support, SLA, or liability insurance — **buyer** operates in production, not **vendor-of-record**.

---

## 3. Who will pay

| Will pay | Will not pay |
|----------|--------------|
| Technical founder acquiring IP | Enterprise procurement seeking turnkey vendor |
| Strategic acquirer engineering team | Dashboard / SIEM / GRC replacement buyer |
| Design-partner CTO (one wedge + spine) | SMB self-serve PLG |

---

## 4. Verification

```bash
make plug
make cg-certification-l4-ci
make demo-gold
python -m spine_core.port_checks
```

---

## Related

- [operational-architecture-scorecard.md](operational-architecture-scorecard.md)
- [maturity-ladder.md](maturity-ladder.md)
- [GOVERNOR-PORTFOLIO.md](../../docs/sales-sheets/GOVERNOR-PORTFOLIO.md)
