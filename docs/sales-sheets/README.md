# Platform sales sheets — index

**Portfolio readiness:** **7.5/10** — [operational-architecture-scorecard.md](../governor-spine-core/docs/operational-architecture-scorecard.md).  
**Primary exit:** pre-hardened source-code IP sale to technical founders / acquirer engineering.

Full specification and maturity packaging for each governor deployment platform. **No commercial pricing in this repo** — scope deals via design-partner SOW and technical proof bundles.

| Platform | Sheet | Primary audience | Maturity tier |
|---|---|---|---|
| **A — Sales Demo** | [01-demo-platform.md](01-demo-platform.md) | Marketing, conferences, first calls | L4 demo · `make demo-gold` |
| **B — Staging / Pilot** | [02-staging-pilot-platform.md](02-staging-pilot-platform.md) | POC in customer VPC | L4 pilot · live provider path |
| **C — Production Institutional++** | [03-production-institutional.md](03-production-institutional.md) | Regulated enterprise, platform teams | L5 · `make plug` + production overlays |
| **D — Enterprise Security Pack** | [04-enterprise-security-pack.md](04-enterprise-security-pack.md) | Zero-trust / InfoSec add-on | L5 security overlay |
| **Insurance Governor — Production** | [insurance-governor-production.md](insurance-governor-production.md) | P&C carriers, claims modernization | L4+L5 · IG live CI |
| **Insurance Governor — Asset sale** | [insurance-governor-tomorrow-sale.md](insurance-governor-tomorrow-sale.md) | Strategic acquirer | Technical proof bundle |
| **Governor portfolio (all SKUs)** | [GOVERNOR-PORTFOLIO.md](GOVERNOR-PORTFOLIO.md) | Acquirers, technical founders | **7.5/10** — see scorecard |
| **Tier-1 carrier PoC playbook** | [06-tier1-carrier-poc-playbook.md](06-tier1-carrier-poc-playbook.md) | Carrier design-partner evaluation | 30–90 day pilot |
| **CRO claims leakage deck** | [07-cro-claims-leakage-deck.md](07-cro-claims-leakage-deck.md) | CRO, Chief Actuary, Lloyd's | 45-min presentation |

## Industry Leading rubric (9/10)

A governor reaches **IL 9/10** only when all five rows are green per [maturity-ladder.md](../governor-spine-core/docs/maturity-ladder.md):

1. L4 CI (`make *-certification-l4-ci`)
2. L5 plug (`make plug`)
3. Live compose-smoke + pilot attestation in CI
4. Hero wedge shell demo (not pytest-only)
5. External design-partner letter or VPC attestation (Phase C)

**Path:** [roadmap-to-industry-leading-9.md](../governor-spine-core/docs/roadmap-to-industry-leading-9.md)

## Quick links

- **All platforms collated demo:** [../demo-all-platforms.md](../demo-all-platforms.md) → `make demo-all-platforms`
- Capability matrix: [../capability-matrix.md](../capability-matrix.md)
- Forensic audit evidence: [../governor-spine-core/docs/forensic-audit-evidence.md](../governor-spine-core/docs/forensic-audit-evidence.md)
- Plug-and-play modes: [../plug-and-play.md](../plug-and-play.md)
- Live demo (Platform A): [../../SALES-DEMO.md](../../SALES-DEMO.md) → `make demo-gold`
