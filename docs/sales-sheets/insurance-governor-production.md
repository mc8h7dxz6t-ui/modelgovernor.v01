# Insurance Governor — Production Institutional++

**SKU:** `IG-PLATFORM-PRODUCTION`  
**Tagline:** Loss-control attestation spine — warranty enforcement, indemnity spend mitigation, UK/US regulatory proof.

---

## Executive summary

Production topology for carriers and MGAs selling **loss control**, not workflow automation. Hash-chained reserves prove policy warranties in real time — reducing claims frequency, severity, and defense-cost reserves across **Cyber, D&O, E&O, and Crime / FI bonds**.

| | |
|---|---|
| **Target buyer** | Financial lines underwriters, CRO, Chief Actuary, wholesale brokers (London / Lloyd's) |
| **Sales motion** | “Deductible reduction via verified controls” → design-partner pilot |
| **Time to live** | 4–8 weeks |
| **Suggested ACV (list)** | **$320K–$850K / year** |
| **Pre-revenue asset worth** | **$2.0M–$4.0M** (11 platforms + warranty mesh) |

---

## Where it sits in the stack

```
┌─────────────────────────────────────────────────────────────────┐
│  Core systems — Guidewire ClaimCenter, Snapsheet, Majesco Claims+ │
│  FNOL webhooks → ClaimGate /claim/fnol/webhook                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Insurance Governor spine (8100–8102)                              │
│  Gateway → Sidecar → Reconciler | hash-chained claim_events        │
└───────┬────────────────────────────────────────────┬──────────────┘
        │                                            │
        ▼                                            ▼
  ClaimGate (8103)                          ZkClaimAudit (8106)
  BindAuthority (8104)                      SpatialTwin (8107)
  ParametricOracle (8105)                   BatteryLiability (8108)
  ModelRiskFreeze (8111)                    SubrogationGraph (8109)
  IndemnityPayGate (8110)                   UnderwritingGovern (8112)
                                            ReserveReconcile (8113)
```

---

## The moat: Warranty Enforcement Engine

Cross-platform mesh rules block commits when policy warranties are breached at runtime.

| Parent | Blocks | Line |
|--------|--------|------|
| ModelRiskFreeze `FROZEN` | ClaimGate, IndemnityPayGate | E&O / Cyber |
| ClaimGate `REFERRED` | IndemnityPayGate | Crime / SIU |
| UnderwritingGovern `VIOLATION` | BindAuthority | D&O |
| ReserveReconcile `DRIFT` | ClaimGate, IndemnityPayGate | Solvency |

See [warranty-enforcement-engine.md](../insurance-governor/warranty-enforcement-engine.md).

---

## Domain wedges (product depth)

### Loss-control wedges (lead with these in financial lines)

| Wedge | Port | Finance analogue | Insurer hook |
|-------|------|------------------|--------------|
| **ModelRiskFreeze** | 8111 | AlgoFreeze | E&O / Cyber catastrophe prevention |
| **IndemnityPayGate** | 8110 | WireMatch | Crime deductible reduction |
| **UnderwritingGovern** | 8112 | CreditGovern | D&O / Consumer Duty compliance |
| **ReserveReconcile** | 8113 | SubledgerSync | Chief Actuary reserve confidence |

### Claims & specialty wedges

| Wedge | Port | Capability | Buyer hook |
|---|---|---|---|
| **ClaimGate** | 8103 | Policy rules, deductibles, SIU referral, ACH payment-rail stub, FNOL ingest | Indemnity frequency & severity |
| **BindAuthority** | 8104 | Premium/limit bind gate | Underwriting modernization |
| **ParametricOracle** | 8105 | Oracle attestation + `/trigger/feed` (HTTP/Chainlink-style) | Cat/parametric triggers |
| **ZkClaimAudit** | 8106 | SHA-256 fact commitments + selective disclosure proofs | Examiner-grade audit story |
| **SpatialTwin** | 8107 | LiDAR point-cloud hash + damage estimate gate | Property / catastrophe spatial |
| **BatteryLiability** | 8108 | SOH / thermal EV battery liability | Auto OEM / fleet programs |
| **SubrogationGraph** | 8109 | Multi-defendant recovery routing | Subrogation desk automation |

---

## Full technical specification

### Deploy

```bash
# Spine + platforms (local rehearsal)
make ig-stack-up

# Pilot attestation (spine + platforms + certification artifact)
make ig-pilot-attestation

# Production Helm
helm lint deploy/helm/insurancegovernor -f deploy/helm/insurancegovernor/values-production.yaml
kubectl apply -f deploy/argocd/application-insurancegovernor-production-helm.yaml
```

### Security & compliance surfaces

| Control | Implementation |
|---|---|
| Authentication | Gateway + sidecar OIDC (`auth_oidc.py`) |
| RBAC | Viewer / claims-admin on `/internal/*` |
| Audit | `admin_audit_log` + hash-chained `claim_events` |
| Tamper evidence | `verify-chain` + S3 Object Lock anchors |
| Platform guard | Registry facet enforcement (422 on missing facets) |
| Degradation | Redis guardrails + circuit breaker fallback |

### Core integration (FNOL)

| Vendor | Adapter | Endpoint |
|---|---|---|
| Guidewire ClaimCenter | `from_guidewire` | `POST /claim/fnol/webhook` |
| Snapsheet | `from_snapsheet` | same |
| Majesco Claims+ | `from_majesco` | same |

Payload shape is normalized to `NormalizedFnol` before policy evaluation and governed commit.

### SLO commitments (institutional++)

| SLO | Target |
|---|---|
| Crystallize/commit availability | **99.5%** / 30d |
| Governed payout p95 | **≤ 500ms** |
| Claim invariants | **Zero budget** — 7-probe `claim_ops` suite |

---

## Packaging & pricing (illustrative)

| SKU component | List (annual) |
|---|---|
| Spine (gateway, sidecar, reconciler, HA kit) | $180K–$400K |
| ClaimGate + FNOL adapter pack | $60K–$120K |
| Headline wedge (pick one at depth) | $40K–$150K each |
| Design-partner attestation + runbook | Included in pilot |

Bundle discount available for spine + ClaimGate + one headline wedge.

---

## Certification

```bash
make ig-spine-test
make ig-certification   # → artifacts/reliability/insurance-governor/latest_attestation.json
```

See [design-partner-attestation.md](../insurance-governor/design-partner-attestation.md) for pilot credibility package.

---

## Related docs

- [institutional-gold-standard.md](../insurance-governor/institutional-gold-standard.md)
- [platform-model.md](../insurance-governor/platform-model.md)
- ModelGovernor production sheet: [03-production-institutional.md](03-production-institutional.md)
