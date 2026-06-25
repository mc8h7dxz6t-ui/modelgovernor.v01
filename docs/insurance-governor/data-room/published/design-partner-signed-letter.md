# Design Partner Attestation Letter (Template)

**Insurance Governor — Enterprise Rehearsal Certification**

Generated: 2026-06-25T16:26:52.402763+00:00

---

This letter attests that **[REDACTED_CARRIER]** (or its authorized representative) participated in a governed Insurance Governor enterprise rehearsal on infrastructure matching production Helm/Istio topology.

## Certified artifacts

| Artifact | SHA-256 |
|----------|---------|
| Cluster attestation | `8ddc4a57c32e0d1c96cda31fa5e725b02b45effcdfb047cfecaecd418101dba2` |
| Certification attestation | `5aef4d4bdd56625ec60c593fdaeebaf0f1964cb588d35788e76221b9b8094c22` |
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
