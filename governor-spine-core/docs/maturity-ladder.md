# Governor Maturity Ladder

**Principle:** Certification labels describe **what was implemented and tested** — not architectural intent.

Authoritative portfolio readiness: [operational-architecture-scorecard.md](operational-architecture-scorecard.md) (**6.5/10** combined).  
Path to **9/10**: [roadmap-to-industry-leading-9.md](roadmap-to-industry-leading-9.md).

---

## Tier map (scores)

| Tier | Score | Label | What it proves |
|------|-------|-------|----------------|
| **L4** | 6–8/10 | Gold Enterprise | CI pyramid + Helm — engineering baseline |
| **L5** | 7–8.5/10 | Institutional Self-Check Certified | `make plug` + portfolio CI |
| **IL** | **9/10** | Industry Leading Gold Standard | L4+L5 + live smoke CI + hero demo + **external evidence** |
| **EV** | **10/10** | Gold-Standard Enterprise Vendor | IL + SOC2/ISO + 24×7 ops + reference customers — **organization**, not repo alone |

---

## Levels

### L4 — Gold Enterprise (6–8/10 implementation band)

**Proves:** pytest pyramid, Postgres vigorous, load smoke, Toxiproxy chaos, Helm enterprise render.

**Commands:** `make *-certification-l4-ci` per governor.

**Does not prove:** Customer VPC production, staffed support, third-party audit.

---

### L5 — Institutional Self-Check Certified

**Proves:** `make plug` — four-governor pytest matrices, port contract, Helm smoke (enforced in CI job `portfolio-plug`).

**Explicit disclaimer** (printed by harness):

> This is NOT third-party enterprise infrastructure audit certification.

**Does not prove:** SOC 2, ISO 27001, DTAC, examiner sign-off.

---

### IL — Industry Leading Gold Standard (**9/10**)

Use **only** when all five rubric rows below are green **per governor**:

1. L4 + L5 gates green  
2. Live attestation in CI (`compose-smoke-*`, `*-pilot-attestation`)  
3. Hero wedge demo shows enforcement in shell (not pytest-only)  
4. External design-partner or acquirer attestation (no stub probes)  
5. Examiner pack archived with `pack_sha256`

---

---

### EV — Gold-Standard Enterprise Vendor (10/10)

**Requires everything in IL (9/10) plus an operating company:**

| # | Requirement | Owner |
|---|-------------|--------|
| 1 | SOC 2 Type II or ISO 27001 (accredited auditor) | Legal / GRC |
| 2 | 24×7 support + published SLA (e.g. 15-min SEV-1) | Operations |
| 3 | Cyber liability + E&O insurance | Finance |
| 4 | ≥2 named reference customers in production | Sales |
| 5 | Vendor-of-record contracts (not IP sale) | Legal |

**The repository alone cannot reach 10/10** — an acquirer or spin-out company must supply EV rows.

---

## What we do not certify

| Claim | Status |
|-------|--------|
| Lamport clocks | Not implemented |
| `InstitutionalModeController` singleton | Not implemented |
| `kubectl patch` on `curl openai.com` | Rejected |
| SOC 2 / ISO from this repo alone | **False** — requires accredited auditor |
| 12-SKU turnkey enterprise platform | **Fantasy path** — see scorecard |

---

## Naming consistency (repo-wide)

| Use | Do not use (without IL evidence) |
|-----|----------------------------------|
| Institutional Self-Check | “SOC2 certified” |
| L4 Gold Enterprise | “Production gold standard vendor” |
| Kernel — industry-leading **class** | “Industry Leading **platform**” |
| Integration **scaffold** | “Shipped enterprise replacement” |

Program manifests: `*/certification/program.yaml` — L5 title = **Institutional Self-Check Certified**.
