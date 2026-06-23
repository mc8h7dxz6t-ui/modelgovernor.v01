# Pre-revenue valuation summary

**As-of:** institutional++ gold-standard packaging (demo stack, production overlays, 57+ Tier-1 tests, GitOps manifests).

This document estimates **what the platform is worth before first dollar of revenue** — for fundraising, M&A conversations, or internal portfolio accounting. Figures are **illustrative ranges**, not appraisals.

---

## Methodology

Three lenses are blended:

| Lens | What it measures | Weight |
|---|---|---|
| **Replacement cost** | Engineering + QA + docs to rebuild from scratch | 40% |
| **Differentiation premium** | Ledger-backed governance, reconciler HA, hash-chain anchor — rare in AI proxy market | 35% |
| **Implied commercial value** | Target ACV × realistic pre-revenue pipeline multiple (0.5–1.5×) | 25% |

Assumptions:

- Loaded engineering cost: **$18K–$22K / engineer-month** (US/EU blended enterprise rate).
- Comparable categories: AI gateway proxies (LiteLLM-class), FinOps control planes, policy sidecars (service-mesh adjacency).
- Pre-revenue infra with production manifests + institutional test suite trades at **$3M–$15M** in recent AI tooling M&A / seed rounds depending on team and pipeline — this repo is **asset-heavy, team-light** positioning.

---

## Per-platform asset worth (pre-revenue)

| Platform SKU | Build effort (equiv.) | Replacement cost | Differentiation | **Asset worth range** |
|---|---|---|---|---|
| A — Sales Demo | 2–3 eng-mo | $40K–$65K | Plug-and-play story, zero-deps demo | **$75K–$150K** |
| B — Staging / Pilot | 4–6 eng-mo | $75K–$130K | K8s + ESO + live provider path | **$400K–$800K** |
| C — Production Institutional++ | 12–18 eng-mo | $220K–$400K | Sentinel, anchor, OIDC, CronJobs, SLOs | **$1.8M–$3.5M** |
| D — Enterprise Security Pack | 3–5 eng-mo | $55K–$110K | Istio egress, mTLS, JWKS live tests | **$350K–$650K** |
| **Cross-cutting IP** (ledger engine, reconciler, 57+ tests, CI tiers) | 10–14 eng-mo | $180K–$310K | Finance invariant suite — hard to replicate | **$900K–$1.6M** |

**Overlap note:** Cross-cutting IP is embedded in C; do not sum naively. Use bundle table below.

---

## Bundle valuation (what you market today)

| Bundle | Includes | Suggested list ACV (when sold) | **Pre-revenue worth (after packaging)** |
|---|---|---|---|
| **Demo + docs only** | Mode A, capability matrix, talk track | N/A (pipeline) | **$150K–$300K** |
| **Pilot package** | A + B | $120K–$250K / yr | **$600K–$1.2M** |
| **Enterprise platform** | A + B + C | $350K–$900K / yr | **$2.5M–$5.5M** |
| **Enterprise + Security** | A + B + C + D | $430K–$1.1M / yr | **$3.5M–$8.5M** |

### Recommended headline number for decks

> **ModelGovernor institutional++ platform (pre-revenue): $4M–$6M fair value**  
> Conservative: $3.5M · Aggressive (strategic buyer): $8.5M

Rationale: full **reserve-before-dispatch** ledger control plane with production K8s/GitOps, tamper-evident audit, and sales-demo-ready packaging sits above “wrapper proxy” repos and below revenue-stage FinOps SaaS.

---

## Revenue path (post first deal)

| Milestone | Typical trigger | Valuation shift |
|---|---|---|
| 1 design-partner LOI | $0 ACV, named logo | +$0.5M–$1M narrative premium |
| First paid pilot ($150K) | Mode B live | 3–5× ACV on that logo → $450K–$750K |
| First production ($400K+ ACV) | Mode C | 8–15× ARR for infra control plane |
| $2M ARR | Multi-tenant + support | $15M–$30M range (category comps) |

---

## What increases worth from here

1. **Named design partners** — even unpaid pilots with Fortune 500 logos.
2. **Managed offering** — hosted control plane (SaaS) multiplies ACV 2–3×.
3. **Compliance artifacts** — SOC 2 Type II report, pen test letter.
4. **Benchmark data** — published invariant / chaos reports under customer NDA.

---

## What is explicitly not in the valuation

- Customer contracts or ARR (pre-revenue by definition).
- OpenAI/Anthropic API resale margin.
- Services revenue from implementation partners (could add $200K–$500K per enterprise deploy).

See individual platform sheets for full technical specs and packaging detail.
