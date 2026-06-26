# Finance Governor — Operations Runbook

Institutional++ failure modes, detection, and operator response.

## Severity classes

| Class | Meaning | Response |
|-------|---------|----------|
| **P1** | Safety invariant breach (zero error budget) | Page on-call; enter diagnostic mode |
| **P2** | SLO burn (availability/latency) | Investigate within 1h |
| **P3** | Degraded non-critical | Next business day |

## Failure mode matrix

### Redis outage

- **Detection:** Sidecar logs Redis connection errors; guardrail reads fall back to local limits
- **Response:** Restore Redis; verify `GET /readyz` on all sidecar pods
- **Do not:** Disable diagnostic mode until invariants clean

### Invariant violation (`regulatory_audit_violation_total`)

- **Detection:** Reconciler post-sweep audit fails; metric increments
- **Automated:** Diagnostic mode — writes return 503, reads return 200
- **Operator:** `GET /internal/diagnostic/status` → identify component/reason
- **Recovery:** Fix data; `POST /internal/diagnostic/clear`; re-run `make fg-forensic-audit`

### Ledger chain tampering

- **Detection:** `ledger_chain_verification_failed_total` or hourly CronJob failure
- **Operator:** `GET /internal/decisions/verify-chain` → note `first_break.event_id`
- **Forensics:** Inspect `decision_events` from break forward; compare S3 anchor head
- **Recovery:** Restore from last known-good anchor; never PATCH events in place

### AlgoFreeze desk FROZEN

- **Detection:** `freeze_state=FROZEN` on `GET /status`; mesh blocks wire/credit/MG reserve
- **Causes:** VERSION_MISMATCH, FEED_DEGRADED
- **Recovery:** Fix feed or approve new deploy SHA via `POST /admin/deploy-registry`; `POST /admin/unfreeze`

### WireMatch HELD wires

- **Detection:** `wire_held_total` increment; no `WIRE_SENT` event
- **Operator:** Adjudicate via compliance UI; do not bypass gate
- **Invariant:** `wire_sent_below_threshold_total` must remain 0

### Reconciler leader loss

- **Detection:** `reconciler_leader == 0` gauge; only one pod holds advisory lock
- **Response:** Check Postgres connectivity; restart standby reconcilers

### Horizon STRANDED crystals

- **Detection:** `reconciler_horizon_strand_total`; escrow status STRANDED
- **Operator:** Manual adjudication required for high/critical risk tiers
- **Never:** Auto-commit or auto-expire high-risk without policy `allow_auto_expire`

## Proof commands

```bash
make fg-forensic-audit          # Full institutional audit
make fg-certification           # Tier 1 certification artifact
make fg-l4-certification        # With Postgres + chaos env vars

curl -H 'x-internal-token: $TOKEN' http://fg-sidecar:8091/internal/decisions/verify-chain
curl -X POST -H 'x-internal-token: $TOKEN' http://fg-sidecar:8091/internal/decisions/anchor-head
```

## CronJob suite (production)

| Job | Schedule | Endpoint |
|-----|----------|----------|
| fg-decision-chain-verify | hourly | `/internal/decisions/verify-chain` |
| fg-decision-chain-anchor | hourly :15 | `POST /internal/decisions/anchor-head` |

## Escalation

1. P1 invariant → diagnostic mode (automatic) → notify CRO + engineering
2. If MG+FG cross-wire blocks all inference → check AlgoFreeze desk state first
3. If chain invalid → halt all commits; preserve Postgres WAL; open forensics ticket
