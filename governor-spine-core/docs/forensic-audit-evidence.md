# Forensic Audit — Evidence-Backed Repository Truth

**Audience:** institutional fund engineers, tech acquirer due diligence  
**Method:** clone → grep → execute CI (`ci.yml`, `fg-ci.yml`) → run `make plug`  
**Portfolio score:** [operational-architecture-scorecard.md](operational-architecture-scorecard.md) (**8.5/10** engineering — IL 9/10 blocked on Phase C only)

Maturity is **implementation, not intent**. High-level narrative claims are secondary to provable code and CI gates. Authoritative machine output: `artifacts/portfolio_self_check.json` (from `make plug`).

---

## 1. The provable engine (defensible moat)

```
                     ┌──────────────────────────────────────────┐
                     │          THE PROVABLE ENGINE             │
                     └──────────────────────────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
   [ THE KERNEL ]                  [ THE PIPELINE ]                 [ THE DEGRADATION ]
  Pre-Execution Blocking          4-Tier CI Integration            Volatile Network Safeties
 (HTTP 409 / 503 fail-closed)   (SQLite → Toxiproxy chaos)        (Circuit breaker, fallbacks)
```

| Capability | Verified by | Location |
|------------|-------------|----------|
| **Pre-execution fail-closed** | pytest + integration tests | `routes_reserve.py`, `routes_crystallize.py`, mesh rules |
| **Tamper-evident hashing** | `verify-chain`, property tests | `*_seal.py`, `test_property_*_chain.py` |
| **4-tier CI pyramid** | GitHub Actions | `.github/workflows/ci.yml`, `fg-ci.yml` |
| **L4 Helm enterprise** | `test_l4_helm_enterprise.py` | `deploy/helm/*/` |
| **CG runtime perimeter (ext_authz)** | `test_l4_runtime_enforcement.py` | `platforms/egress_govern/`, mesh tests |

**Kernel score: 9.0/10** — industry-leading **class** architecture with CI proof (K1/H1/K3/K4/M1 conformance).

---

## 2. Honest product gaps (backlog)

| Layer | Status | Score |
|-------|--------|-------|
| **Four governor spines (L4 CI)** | Complete — kernels pass L4 gates | 8.5/10 |
| **ModelGovernor demo-gold** | Functional demo suite | 7.0/10 |
| **Demo wedges** (AlgoFreeze, WireMatch, EgressGovern, ClaimGate) | Demo-ready | 6–7/10 |
| **Integration scaffolds** (SubledgerSync, CreditGovern, ThreatProxy, …) | API + schema; buyer SOW | 6.0/10 |
| **Secondary IG wedges** (SpatialTwin, SubrogationGraph) | Governed evidence envelope + mock vendor feed + demo/CI | **7.5/10** |
| **IG FNOL modules** | Payload **normalizers** — not live PAS connectors | 6.0/10 |

---

## 3. Unified compliance language

| Use everywhere | Do not use without external evidence |
|----------------|-------------------------------------|
| **L5 Institutional Self-Check Certified** | L5 Industry Leading |
| **L4 Gold Enterprise** (CI gate) | L5 Enterprise (ambiguous) |
| **Kernel — industry-leading class** (8.5/10) | Industry Leading **platform** |
| **Integration scaffold** | Turnkey enterprise replacement |

Authoritative ladder: [maturity-ladder.md](maturity-ladder.md)

**Removed from repo** (unaudited self-grades): `docs/architecture-scalability-rating.md` (92/100), `docs/institutional-hardening-forensic-audit.md` (91/100).

---

## 4. Verification commands (reproducible)

```bash
make plug                                    # L5 Institutional Self-Check (enforced in CI)
make cg-certification-l4-ci
make fg-certification-l4-ci
make ig-certification-l4-ci
```

CI workflows: `.github/workflows/ci.yml`, `.github/workflows/fg-ci.yml`, job `portfolio-plug`.

---

## 5. Exit positioning

| Path | Fit |
|------|-----|
| **Pre-hardened source-code IP sale** | ✅ Matches 7.5/10 asset |
| **L5 12-SKU enterprise vendor procurement** | ❌ Blocked — no SOC2 org, no support SLA |

See [transactional-kernel-strategy.md](transactional-kernel-strategy.md) and [GOVERNOR-PORTFOLIO.md](../../docs/sales-sheets/GOVERNOR-PORTFOLIO.md).
