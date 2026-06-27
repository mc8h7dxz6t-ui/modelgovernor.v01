# ParametricOracle — Oracle-Attested Parametric Trigger

**Standalone platform** for governed parametric payouts with external oracle attestation.

## Problem

Parametric products pay on index triggers without cryptographic proof of what the oracle reported at commit time.

## Solution

- **Oracle attestation hash** — SHA-256 over `source:payload`; 422 on mismatch
- **Threshold evaluation** — TRIGGERED only when verified metric ≥ threshold
- **CCP crystal** — crystallize oracle evidence; commit on TRIGGERED

## API

```
POST /trigger/evaluate
GET  /healthz
GET  /readyz
```

## Tests

```bash
pytest insurance-governor/tests/test_parametric_oracle.py -q
```
