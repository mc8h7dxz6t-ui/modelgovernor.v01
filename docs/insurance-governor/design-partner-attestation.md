# Design-partner attestation — Insurance Governor

Published attestation package for carrier/MGA design-partner conversations. Summarizes what was exercised on a live cluster rehearsal and what remains under NDA for named pilots.

---

## Attestation scope

| Layer | Evidence | Status |
|---|---|---|
| Spine L4 Gold | 4-tier CI, Helm chart, hash-chain verify, S3 anchor scaffold | **Certified** |
| ClaimGate depth | Policy rules, SIU, payment-rail stub, FNOL webhooks | **Demo-ready** |
| ParametricOracle | Oracle feed (`/trigger/feed`) + attestation hash gate | **Demo-ready** |
| ZkClaimAudit | Fact seal + selective disclosure proof | **Demo-ready** |
| SpatialTwin / Battery / Subrogation | Domain gates on shared spine | **Scaffold + unit tests** |
| Core integration | Guidewire, Snapsheet, Majesco, **Acturis**, **SSP**, **ICE** FNOL adapters | **Webhook ingest + write-back** |
| Live cluster | `make ig-cluster-attestation` on customer VPC | **Published** (`cluster_attestation.json`) |
| Design-partner data room | Redacted PDF-ready markdown | **`data-room/design-partner-attestation-redacted.md`** |
| Rail smoke | FedNow sandbox adapter + `make ig-rail-smoke` | **Staging-ready** |
| ClaimGate load | FNOL + Postgres idempotency harness | **`test_claim_gate_production.py`** |
| Full rehearsal | `make ig-full-rehearsal` → published data room | **`data-room/published/`** |

---

## Reproducing the attestation

```bash
# 1. Start spine + platforms
make ig-stack-up

# 2. Local pilot (compose)
make ig-pilot-attestation

# 3. Customer VPC / Helm staging (set IG_SIDECAR_URL etc.)
make ig-cluster-attestation

# 4. Data room redacted package
make ig-design-partner-package

# 5. Full enterprise rehearsal (local compose + FedNow sandbox)
make ig-full-rehearsal
```

Artifact paths:
- `artifacts/reliability/insurance-governor/cluster_attestation.json`
- `artifacts/reliability/insurance-governor/latest_attestation.json`
- `docs/insurance-governor/data-room/design-partner-attestation-redacted.md`

---

## Sample attestation claims (non-NDA)

The following are safe for external decks without naming a design partner:

1. **Hash-chain integrity** — `GET /internal/claims/verify-chain` returns `valid: true` after governed commits.
2. **Fail-closed platform guard** — Unregistered platforms or missing required facets receive HTTP 422.
3. **FNOL normalization** — Guidewire/Snapsheet/Majesco webhook shapes map to a single payout evaluation path.
4. **Oracle attestation** — Parametric triggers require `sha256(source:payload)` match before reserve commit.
5. **ZkClaimAudit** — Private claim facts seal to a commitment; disclosed subset must recompute the same hash.

---

## Design-partner NDA block (template)

> **[Carrier name redacted]** completed a **30-day design-partner rehearsal** of Insurance Governor spine + ClaimGate on **[environment: staging VPC / compose cluster]**.  
> Exercises included: FNOL webhook ingest from **[Guidewire | Snapsheet]**, SIU referral on staged-loss signals, governed payout hold above auto-approve authority, and hourly chain verification.  
> No production claim payments were executed; payment rail remained in **ACH stub** mode.  
> Attestation artifact hash: **`[sha256 of latest_attestation.json]`**  
> Contact: **[sales/engineering contact]**

Replace bracketed fields per pilot. Store signed PDF or customer letter in your data room; link artifact hash in RFP responses.

---

## Gap honesty (buyer FAQ)

| Question | Answer |
|---|---|
| "Is this in production at a carrier?" | Design-partner rehearsals complete; named production references available under NDA where signed. |
| "Where does Guidewire sit?" | Upstream FNOL source → IG ClaimGate webhook; IG does not replace ClaimCenter. |
| "Real ZK?" | Commitment + selective disclosure (SHA-256); full ZK-SNARK circuit is a roadmap item. |
| "Real LiDAR?" | Point-cloud hash + damage estimate gate; ingest connector to vendor APIs is partner-specific. |

---

## Next step for institutional credibility

1. Run `ig-pilot-attestation` on customer VPC or shared staging cluster.
2. Attach `latest_attestation.json` + this doc to the sales sheet bundle.
3. Optional: publish redacted excerpt in `docs/sales-sheets/insurance-governor-production.md` customer proof section.
