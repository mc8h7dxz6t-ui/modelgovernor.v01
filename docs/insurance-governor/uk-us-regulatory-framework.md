# UK & US Regulatory Framework — Insurance Governor

Jurisdiction-specific standards mapped to platform controls. Use in RFPs, Lloyd's coverholder audits, and US state DOI examinations.

---

## United Kingdom

| Standard | Body | Platform control | Evidence artifact |
|----------|------|------------------|-------------------|
| **Consumer Duty** (PS22/3) | FCA | UnderwritingGovern — fair outcomes, bias scoring | `govern_decision` crystal + adverse action flag |
| **SS1/23** Model risk | PRA | ModelRiskFreeze — approved version registry | `freeze_state` + `model_version` facets |
| **Solvency II** (technical provisions) | PRA / Lloyd's | ReserveReconcile — case vs reinsurance drift | `match_state`, `drift_amount` |
| **Equality Act 2010** | UK law | UnderwritingGovern — protected attribute deltas | `bias_score`, `govern_decision=VIOLATION` |
| **UK GDPR / ICO** | ICO | ZkClaimAudit — selective disclosure commitments | `commitment_hash`, examiner prove path |
| **Lloyd's Minimum Standards** | Lloyd's | Spine hash chain + mesh warranties | `verify-chain`, mesh block audit |
| **IDD** (Insurance Distribution) | FCA | BindAuthority + UnderwritingGovern mesh | No bind on `VIOLATION` |

### UK policy pack (seeded)

| Policy ID | Platform | Jurisdiction |
|-----------|----------|--------------|
| `claim-high-uk` | ClaimGate | UK |
| `bind-standard-uk` | BindAuthority | UK |
| `crime-indemnity-uk` | IndemnityPayGate | UK |
| `model-risk-uk` | ModelRiskFreeze | UK |
| `underwriting-fair-uk` | UnderwritingGovern | UK |
| `reserve-sync-uk` | ReserveReconcile | UK |
| `POL-MOTOR-UK-001` | ClaimGate rules engine | UK motor |

Currency: GBP supported via `currency` facet; reserve ledgers default USD in spine — production overlays should add GBP ledger rows.

---

## United States

| Standard | Body | Platform control | Evidence artifact |
|----------|------|------------------|-------------------|
| **ECOA / Reg B** | CFPB / Fed | UnderwritingGovern | Adverse action required flag |
| **FCRA** | FTC / CFPB | UnderwritingGovern | Per-decision bias audit trail |
| **NAIC Model Audit Rule** | State DOI | Spine `claim_events` hash chain | `verify-chain`, S3 anchors |
| **State unfair discrimination** | State DOI | UnderwritingGovern + policy rules | Jurisdiction facet on crystals |
| **SOC 2 Type II** (cyber) | AICPA | ModelRiskFreeze + OIDC RBAC | Freeze + access audit |
| **SR 11-7** (model risk, banks) | OCC / Fed | ModelRiskFreeze (analogue for insurers) | Version registry API |

### US policy pack (seeded)

| Policy ID | Platform | Line |
|-----------|----------|------|
| `claim-high-us` | ClaimGate | P&C casualty |
| `crime-indemnity-us` | IndemnityPayGate | Crime / fidelity |
| `model-risk-us` | ModelRiskFreeze | Cyber / E&O |
| `underwriting-fair-us` | UnderwritingGovern | Commercial / personal lines |
| `reserve-sync-us` | ReserveReconcile | Reinsurance |

---

## Cross-jurisdiction mesh (same engine, different policy IDs)

Mesh rules are **jurisdiction-agnostic** — enforcement is on facet values, not geography. Deploy UK and US policy packs side by side; crystals carry `jurisdiction` facet for examiner export.

---

## FNOL / core systems (US-heavy today)

| Vendor | Region | Adapter |
|--------|--------|---------|
| Guidewire ClaimCenter | US / UK | `fnol_adapter.from_guidewire` |
| Snapsheet | US | `from_snapsheet` |
| Majesco | US | `from_majesco` |
| **Acturis** | UK | `from_acturis` |
| **SSP (Open Claims / Pure)** | UK | `from_ssp` |

---

## Examiner questions → answers

| Question | Answer |
|----------|--------|
| “Prove model version in production matched approved?” | `GET /status` on ModelRiskFreeze + crystal history |
| “Prove no payment during SIU hold?” | Mesh block log + `gate_decision=REFERRED` parent crystal |
| “Prove reserve matched reinsurance bordereaux?” | ReserveReconcile `MATCHED` crystal before ClaimGate commit |
