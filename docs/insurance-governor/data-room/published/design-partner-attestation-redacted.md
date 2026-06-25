# Design-Partner Attestation (Redacted)

**Document classification:** Data room — NDA redacted excerpt  
**Generated:** 2026-06-25T14:47:49.404565+00:00  
**Design partner:** [REDACTED_CARRIER]  
**Environment:** local-embedded-rehearsal  

---

## Executive summary

[REDACTED_CARRIER] completed a **30-day design-partner rehearsal** of Insurance Governor on a **local-embedded-rehearsal** cluster. The attestation exercise validated governed claim commits, hash-chain integrity, ClaimGate FNOL ingest (US + UK PAS), and Postgres-backed payment idempotency under load.

| Metric | Result |
|--------|--------|
| Attestation probes passed | **7 / 7** |
| Pilot attestation SHA-256 | `3983a2a3f6cdcf4e20dbdc61b38cd53aba15cf270fb8cccd7465999a74b4a172` |
| Certification artifact SHA-256 | `8ff7a9bbd5259018f79c0627d311f372872fa441baf480414e3648e69849f57c` |
| Payment rail mode | Staging sandbox (no production funds) |

---

## Exercises completed (redacted)

1. **Spine L4** — governed commit, `verify-chain`, S3 anchor head  
2. **ClaimGate depth** — policy rules, SIU path, FNOL Guidewire + **Acturis UK** webhook  
3. **Postgres idempotency** — `payment_idempotency` table; duplicate keys return same `payment_id`  
4. **Warranty mesh** — cross-platform blocks at commit (model freeze → payout block)  
5. **Staging rail smoke** — FedNow sandbox token exercised (`PAYMENT_RAIL_MODE=fednow_sandbox`)  

---

## Safe external claims

- Hash-chained `claim_events` verified tamper-free after governed operations  
- FNOL normalized from Guidewire, Snapsheet, Majesco, **Acturis**, **SSP (UK)**  
- Fail-closed platform guard on unregistered facets (HTTP 422)  
- No production claim payments; staging rail sandbox only  

---

## Artifact references

| File | Path |
|------|------|
| Cluster attestation | `artifacts/reliability/insurance-governor/cluster_attestation.json` |
| Certification | `artifacts/reliability/insurance-governor/latest_attestation.json` |
| Full methodology | `docs/insurance-governor/design-partner-attestation.md` |

---

## NDA notice

Carrier legal name, VPC identifiers, and IdP tenant IDs are redacted. Full signed design-partner letter available under mutual NDA.

*This document is suitable for investor data room and wholesale broker RFP appendices.*
