# Design Partner Attestation Letter (Template)

**Insurance Governor — Enterprise Rehearsal Certification**

Generated: 2026-06-25T13:38:43.014966+00:00

---

This letter attests that **[REDACTED_CARRIER]** (or its authorized representative) participated in a governed Insurance Governor enterprise rehearsal on infrastructure matching production Helm/Istio topology.

## Certified artifacts

| Artifact | SHA-256 |
|----------|---------|
| Cluster attestation | `89aac1f91b42bff0d67690ed5a12184475b2e53374f59893e61f70398a3500b1` |
| Certification attestation | `1efda47629cce76c002b45e6de276ee9f7d332a994236f7fb75e44af3b4b5d5a` |

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
