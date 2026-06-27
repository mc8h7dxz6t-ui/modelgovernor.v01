# Insurance Governor — automated rehearsal checklist

> **Not** “100% production carrier completion.” FNOL rows = webhook shape adapters; live PAS = SOW.

| Layer | Item | Status |
|-------|------|--------|
| **Spine** | L4 hash-chain, reconciler, gateway | Done |
| **Spine** | Postgres state, payment idempotency, commitments | Done |
| **Platforms** | 11 governed platforms (8100–8113) | Done |
| **ClaimGate** | Policy rules, SIU, payment rail | Done |
| **ClaimGate** | FNOL US (Guidewire, Snapsheet, Majesco) | Done (shape adapters) |
| **ClaimGate** | FNOL UK (Acturis, SSP, ICE InsureTech) | Done (shape adapters) |
| **ClaimGate** | FNOL write-back (Guidewire, Acturis, ICE) | Done (stub write-back) |
| **ClaimGate** | Load harness + Postgres idempotency | Done |
| **Oracle** | Live feeds + attestation gate | Done |
| **Rails** | FedNow sandbox + smoke script | Done |
| **UK** | GBP reserve ledger + motor policy (0009) | Done |
| **Mesh** | UK/US warranty crystal mesh rules | Done |
| **Infra** | Helm, Istio mTLS, migration bundle | Done |
| **CI** | 4-tier tests + migration invariants | Done |
| **CI** | Full enterprise rehearsal job | Done |
| **GTM** | Sales sheet, persona mapping, regulatory framework | Done |
| **GTM** | Design-partner attestation + data room | Done |
| **GTM** | Published cluster/certification artifacts | Done |
| **GTM** | Signed letter template + integration architecture | Done |
| **Human** | Named carrier NDA + live VPC sign-off | Partner step |
| **Depth** | SpatialTwin/Battery/Subrogation vendor connectors | Optional phase 2 |

**Automated completion:** enterprise rehearsal path is fully scripted via `make ig-full-rehearsal`.
