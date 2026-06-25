# Insurance Governor — Production Institutional++

**SKU:** `IG-PLATFORM-PRODUCTION`  
**Tagline:** Governed claims spine — hash-chained reserves, policy-gated payouts, core-system FNOL ingest.

---

## Executive summary

Production topology for carriers and MGAs that need tamper-evident claim commits, SIU-aware payout gates, and plug-and-play domain wedges (ClaimGate, ZkClaimAudit, ParametricOracle, SpatialTwin, EV battery liability, subrogation graph) on a shared spine.

| | |
|---|---|
| **Target buyer** | P&C carriers, MGAs, insurtech platform teams, claims modernization programs |
| **Sales motion** | Design-partner pilot → production rollout on shared spine |
| **Time to live** | 4–8 weeks (managed Postgres, IdP, core webhook integration) |
| **Suggested ACV (list)** | **$280K–$750K / year** |
| **Pre-revenue asset worth** | **$1.5M–$3.0M** |

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
                                            SubrogationGraph (8109)
```

---

## Domain wedges (product depth)

| Wedge | Port | Capability | Buyer hook |
|---|---|---|---|
| **ClaimGate** | 8103 | Policy rules, deductibles, SIU referral, ACH payment-rail stub, FNOL ingest | "Governed payout before money moves" |
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
