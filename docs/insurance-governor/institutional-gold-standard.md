# Institutional++ Gold Standard — Insurance Governor

Testable requirements inherited from ModelGovernor, applied per platform and on the optional spine.

## Definition

**Institutional++** = controls satisfying engineering, operations, and compliance audiences simultaneously.

## Platform baseline (every extractable platform)

| Control | Verification |
|---------|--------------|
| Pre-execution gate | No payout/bind without policy check |
| Append-only events | `platform_events` or spine `claim_events` |
| Idempotency | Replay test on operation_id |
| Exact decimal | `Decimal` / `NUMERIC(24,12)` |
| `/healthz`, `/readyz` | K8s probes |
| Standalone boot | Single compose command |
| Diagnostic mode | Writes 503 when spine in incident |

## Spine extensions (optional)

| Control | Insurance Governor implementation |
|---------|-----------------------------------|
| Hash-chained events | `claim_seal.py` on all paths including sweeps |
| Verify chain API | `GET /internal/claims/verify-chain` |
| claim_ops probes | 7 invariant classes, zero error budget |
| Reconciler halt | Sweeps skip when diagnostic mode active |
| CCP | `platforms/common/crystal.py` |

## Zero error budget signals

| Counter | Meaning |
|---------|---------|
| `surprise_commit_blocked_total` | Commit without valid crystal |
| `crystal_fingerprint_mismatch_total` | Facet drift at commit |
| `negative_balance_detected_total` | Reserve ledger breach |
| `duplicate_commit_anomaly_total` | Double payout attempt |
| `stranded_without_hold_total` | STRANDED without STRANDED_HOLD event |
| `claim_chain_verification_failed_total` | Tamper detected |

## Certification commands

```bash
make ig-spine-test          # Tier 1 SQLite integration
make ig-spine-smoke         # Live stack smoke (requires compose up)
```

Tier 2–4 (Postgres vigorous, load, chaos) — target parity with ModelGovernor CI; see `docs/reliability-testing.md`.
