# ClaimGate — Governed Payout Gate

**Standalone platform** preventing silent or ungoverned claim payouts.

## Problem

Claims systems auto-adjudicate above threshold without immutable evidence of what was known at payout authorization. Examiners cannot reconstruct governed conditions years later.

## Solution

Pre-payout gate:

- **Policy limit check** — block above coverage limit
- **Auto-approve threshold** — HELD above carrier policy band
- **SIU referral** — REFERRED on fraud flag (never auto-pay)
- **CCP crystal** — crystallize facets at evaluation; commit only on APPROVED

## Deployment modes

| Mode | Command | Dependencies |
|------|---------|--------------|
| Standalone | `docker compose -f docker-compose.standalone.yml up` | ClaimGate only |
| Spine-connected | `IG_SPINE_ENABLED=true` in root compose | + ig-sidecar |

## Standalone architecture

```
FNOL / adjuster ──► ClaimGate ──► Payment rail (mock)
                         │
              payout_gate + SpineAdapter (local mode)
                         │
                 platform_events (SQLite)
```

## Core invariants

| Invariant | Enforcement |
|-----------|-------------|
| No payout above policy limit | `payout_gate.py` |
| SIU flag never auto-approves | `evaluate_payout` |
| HELD never commits without adjudication | No commit on HELD/REFERRED |
| Exact decimal amounts | Pydantic + `Decimal` |

## API

```
POST /claim/evaluate
GET  /healthz
GET  /readyz
```

## Tests

```bash
pytest insurance-governor/tests/test_claim_gate.py -q
```
