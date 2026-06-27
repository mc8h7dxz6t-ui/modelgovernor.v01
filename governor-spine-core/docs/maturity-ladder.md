# Governor Maturity Ladder

**Principle:** Certification labels describe **what was implemented and tested** — not architectural intent.

Authoritative portfolio readiness: [operational-architecture-scorecard.md](operational-architecture-scorecard.md) (**6.5/10** combined).

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

### IL — Industry Leading Gold Standard (kernel architecture class only)

Use **only** when:

1. L4 + L5 gates green on release branch  
2. Live attestation (`cg-pilot-attestation`, `compose-smoke-cg`) in reference VPC  
3. External or design-partner evidence (no stub `probes_note`)  

**Industry Leading** = **kernel design grade** (8.5/10 spine), **not** portfolio vendor grade (6.5/10).

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
