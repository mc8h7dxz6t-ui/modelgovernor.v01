# Design-Partner Attestation (Redacted)

**Document classification:** Data room — NDA redacted excerpt  
**Generated:** 2026-06-25T16:26:49.231989+00:00  
**Design partner:** [REDACTED_CARRIER]  
**Environment:** local-embedded-rehearsal  

---

## Executive summary

[REDACTED_CARRIER] completed a **30-day design-partner rehearsal** of Insurance Governor on a **local-embedded-rehearsal** cluster. The attestation exercise validated governed claim commits, hash-chain integrity, ClaimGate FNOL ingest (US + UK PAS), and Postgres-backed payment idempotency under load.

| Metric | Result |
|--------|--------|
| Attestation probes passed | **7 / 7** |
| Pilot attestation SHA-256 | `c9cdef3ffdf79f6988689e5284faa7a3352e8c30e8545efb3301fd5833e0383e` |
| Certification artifact SHA-256 | `5aef4d4bdd56625ec60c593fdaeebaf0f1964cb588d35788e76221b9b8094c22` |
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
