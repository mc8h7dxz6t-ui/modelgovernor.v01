# Design Partner Attestation Letter (Template)

**Insurance Governor — Enterprise Rehearsal Certification**

Generated: 2026-06-25T14:47:52.280889+00:00

---

This letter attests that **[REDACTED_CARRIER]** (or its authorized representative) participated in a governed Insurance Governor enterprise rehearsal on infrastructure matching production Helm/Istio topology.

## Certified artifacts

| Artifact | SHA-256 |
|----------|---------|
| Cluster attestation | `15a4715bd7571ecdfdd0e210541742de76c32cb141d189b5433de836d590a8b0` |
| Certification attestation | `8ff7a9bbd5259018f79c0627d311f372872fa441baf480414e3648e69849f57c` |
| Live probes passed | **7 / 7** |

## Scope exercised

1. **Spine L4** — Hash-chain verify, governed commit, reserve ledger, horizon reconciliation
2. **ClaimGate** — Policy engine, SIU workflow, FNOL webhooks (US + UK PAS), payment rail sandbox
3. **ParametricOracle** — Live oracle feed with attestation hash gate
4. **Loss-control wedges** — IndemnityPayGate, ModelRiskFreeze, UnderwritingGovern, ReserveReconcile
5. **Warranty mesh** — Cross-platform crystal mesh rules enforced at commit time

## Signatures

| Role | Name | Date |
|------|------|------|
| Carrier / MGA sponsor | __________________ | __________ |
| Insurance Governor delivery | __________________ | __________ |

---

*Redacted template — replace placeholders before execution. Live hashes are published in `data-room/published/manifest.json`.*
