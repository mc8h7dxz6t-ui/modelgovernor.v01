# IP Licensing Framework — SKU Matrix

**Purpose:** Structure intellectual-property grants for acquirers, Tier-1 carriers, MGAs, and VPC perpetual buyers. Aligns with the three governors and twelve commercial module SKUs.

**Status:** Pre-revenue asset sale / design-partner template — legal counsel must finalize grant language.

---

## 1. IP inventory (what is licensed)

| Layer | Assets | Protection | Notes |
|-------|--------|------------|-------|
| **Core spine** | Reserve-before-commit ledger, hash-chained events, reconciler leader election, crystal mesh | Trade secret + copyright | Shared pattern across MG / FG / IG |
| **Governor platforms** | ModelGovernor, Finance Governor, Insurance Governor (11 IG wedges) | Copyright + documentation |
| **Commercial modules** | Twelve VPC SKUs (see §3) | Per-module copyright |
| **Operations IP** | Helm charts, Kustomize overlays, CI certification tiers, attestation runners | Copyright |
| **Brand** | ModelGovernor™, governor product names (as used in docs) | Trademark (register separately) |
| **Data / models** | None shipped — buyer data stays in buyer VPC | N/A |

**Explicitly excluded unless separately negotiated:** buyer-specific FNOL credentials, production API keys, named carrier attestations under NDA, SaaS multi-tenant hosting rights.

---

## 2. License archetypes

| Archetype | Code | Typical buyer | Term | Field of use |
|-----------|------|---------------|------|--------------|
| **Evaluation** | `EVAL` | Tier-1 carrier PoC | 30–90 days | Non-production, capped claims volume |
| **Design-partner** | `DP` | Carrier / MGA pilot | 12 months | Staging VPC, single legal entity |
| **Annual VPC subscription** | `SUB-VPC` | Enterprise platform team | 1 yr renewable | Buyer VPC, unlimited internal users |
| **Perpetual VPC** | `PERP-VPC` | Strategic acquirer / bank IT | Perpetual | Buyer VPC + 12-mo updates (maintenance SOW) |
| **OEM / embedded** | `OEM` | PAS vendor, TPA, insurtech | Per deal | Embed in named product; revenue share |
| **Source escrow** | `ESCROW` | Regulated buyer add-on | Tied to `SUB` or `PERP` | Release on vendor insolvency trigger |

### Standard restrictions (all archetypes)

- No resale of unmodified stack as competing multi-tenant SaaS without `OEM` schedule.
- No removal of hash-chain / attestation hooks in `PERP-VPC` without written waiver (examiner integrity).
- Audit right: buyer may run `make *-certification` and `*-examiner-evidence` annually; logs retained 7 years.
- Export control: US/UK/EU financial services and insurance operations only unless expanded.

---

## 3. SKU matrix — license mapping

### 3A. Platform governors (spine bundles)

| SKU ID | Product | License default | List band (annual VPC)* | Perpetual VPC* | Evaluation |
|--------|---------|-----------------|-------------------------|----------------|------------|
| `MG-PLATFORM-DEMO` | ModelGovernor demo | Included / lead-gen | — | — | Open |
| `MG-PLATFORM-STAGING` | Staging / pilot | `EVAL` → `DP` | £25K–£55K | — | 60 days |
| `MG-PLATFORM-PRODUCTION` | Production institutional++ | `SUB-VPC` | £95K–£220K | £180K–£420K | 30 days read-only |
| `MG-ADDON-ENTERPRISE-SECURITY` | Istio / mTLS pack | Add-on to MG-C | £35K–£85K | £70K–£150K | With parent |
| `FG-PLATFORM-PRODUCTION` | Finance Governor (5 platforms) | `SUB-VPC` | £85K–£200K | £160K–£380K | 30 days |
| `IG-PLATFORM-PRODUCTION` | Insurance Governor spine + 11 wedges | `SUB-VPC` | £90K–£240K | £175K–£450K | 30 days |
| `IG-ADDON-ENTERPRISE-SECURITY` | IG Istio + zero-trust spine ingress | Add-on to IG | £30K–£75K | £60K–£130K | With parent |

\*Illustrative GBP list from consolidated catalog; USD OBO asset sale uses separate bundle (see `valuation-pre-revenue.md`).

### 3B. Twelve commercial module SKUs (VPC modules)

| # | SKU ID | Module | Governor affinity | Standalone license | Typical bundle |
|---|--------|--------|-------------------|--------------------|----------------|
| 1 | `SKU-COMPLIANCE-LOGGER` | Compliance Logger | MG / FG | `SUB-VPC` | MG-C + D |
| 2 | `SKU-PROXY-RISK` | Proxy-Risk | MG | `SUB-VPC` | MG-C |
| 3 | `SKU-ALT-DATA` | Alt-Data | FG | `SUB-VPC` | FG-C |
| 4 | `SKU-AI-KIT` | AI Kit | MG | `SUB-VPC` | MG-C |
| 5 | `SKU-WEBHOOK-MESH` | Webhook Mesh | MG / IG | `SUB-VPC` | IG-C (FNOL) |
| 6 | `SKU-AD-GUARD` | Ad Guard | MG | `SUB-VPC` | MG-C |
| 7 | `SKU-HEALTH-TELEMETRY` | Health Telemetry | Cross | `SUB-VPC` | Ops add-on |
| 8 | `SKU-MODEL-GOVERNOR` | ModelGovernor (module) | MG | `SUB-VPC` | = MG-C core |
| 9 | `SKU-DRIFT-GATE` | Drift Gate | FG / IG | `SUB-VPC` | IG ModelRiskFreeze |
| 10 | `SKU-WEBHOOK-REPLAY` | Webhook Replay | MG / IG | `SUB-VPC` | IG ClaimGate |
| 11 | `SKU-SPEND-GUARD` | Spend Guard | MG | `SUB-VPC` | MG-C |
| 12 | `SKU-AGENT-LEDGER` | Agent Ledger | MG / FG | `SUB-VPC` | MG-C + FG-C |

**Bundle pricing rule:** Full 12-module perpetual VPC list ≈ **£92.7K**; all-12 annual prepay ≈ **£115.3K/yr** (1 seat, 1 feed baseline). Spine governors sold separately or as `ENTERPRISE-ALL` package.

### 3C. Composite packages (recommended GTM)

| Package ID | Includes | License | Target |
|------------|----------|---------|--------|
| `BUNDLE-PILOT` | `MG-B` or `IG-EVAL` + attestation | `DP` | First 90 days |
| `BUNDLE-FINLINES` | `IG-PLATFORM-PRODUCTION` + ClaimGate + 1 wedge | `SUB-VPC` | P&C carrier |
| `BUNDLE-ENTERPRISE-ALL` | 3 governors + 12 modules + security packs | `PERP-VPC` | Acquirer / bank holding co |
| `BUNDLE-OEM-PAS` | `IG` FNOL adapters + mesh API | `OEM` | Guidewire ISV partner |

---

## 4. Grant schedule (contract exhibits)

Use three exhibits in every enterprise order form:

### Exhibit A — Licensed SKUs

Checkbox table of SKU IDs from §3 with quantity (seats, feeds, VPC instances).

### Exhibit B — Technical boundaries

| Boundary | Licensed | Not licensed |
|----------|----------|--------------|
| Deploy target | Named AWS account / K8s cluster IDs | Other clouds without amendment |
| Connectors | Stubs + adapter SDK in repo | Buyer prod API keys (buyer procures) |
| Updates | Git tags per maintenance year | Custom feature dev (SOW) |
| Support | Runbooks + certification targets | 24×7 NOC (optional SOW) |

### Exhibit C — Attestation & audit

- Minimum certification: **L4 Gold** (`make ig-certification-l4-ci` or governor equivalent).
- Buyer may request **examiner evidence pack** (`make ig-examiner-evidence`) within 10 business days annually.
- Hash of `latest_attestation.json` recorded in order form appendix.

---

## 5. Royalty & OEM economics (optional)

| Model | Rate | When |
|-------|------|------|
| **Internal use** | $0 royalty | `SUB-VPC` / `PERP-VPC` |
| **OEM embed** | 8–15% of module gross | PAS/TPA resells to policyholders |
| **Revenue share pilot** | 0% Yr1 → 5% Yr2+ | `DP` converts to OEM |
| **Acquirer asset sale** | One-time | All IP assignment — no royalty |

---

## 6. Escrow & insolvency

| Trigger | Release |
|---------|---------|
| Vendor insolvency filing | Full source for licensed SKUs |
| Maintenance lapse > 90 days | Read-only Git bundle + Helm charts |
| Critical CVE unpatched > 60 days | Patch branch or escrow release |

Escrow agent: neutral third party (e.g. Iron Mountain / EscrowTech). Deposit: tagged release matching Exhibit A.

---

## 7. Acquisition / asset-sale framing

For **Acquire.com** or strategic LOI:

> Buyer receives perpetual `PERP-VPC` license to entire repo IP (3 governors + 12 modules + deploy artifacts), assignment of copyright, and 90-day transition assistance. No customer contracts transfer (pre-revenue). Buyer commercializes under own entity; seller retains no SaaS operating obligation.

Recommended ask context: **$4.99M OBO** with IP schedule as Exhibit 1 to asset purchase agreement.

---

## Related

- [README — sales sheet index](README.md)
- [Insurance Governor production](insurance-governor-production.md)
- [Valuation pre-revenue](valuation-pre-revenue.md)
- [Design-partner attestation](../insurance-governor/design-partner-attestation.md)
