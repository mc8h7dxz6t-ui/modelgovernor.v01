-- Institutional-grade DB backstops for control-plane invariants.
-- Application logic remains authoritative; these constraints catch races and bugs.

-- Trace cap: reserved_total must never exceed cap_amount at rest.
ALTER TABLE trace_budget_state
    ADD CONSTRAINT trace_budget_reserved_within_cap
    CHECK (reserved_total <= cap_amount);

-- Non-negative trace aggregates.
ALTER TABLE trace_budget_state
    ADD CONSTRAINT trace_budget_nonnegative_totals
    CHECK (reserved_total >= 0 AND settled_total >= 0 AND cap_amount >= 0);

-- Exactly one expiry refund event per operation (reconciler idempotency backstop).
CREATE UNIQUE INDEX IF NOT EXISTS ledger_events_one_expired_sweep_per_op
    ON ledger_events (idempotency_key)
    WHERE event_type = 'EXPIRED_SWEEP';

-- Exactly one terminal settlement event per operation.
CREATE UNIQUE INDEX IF NOT EXISTS ledger_events_one_terminal_settle_per_op
    ON ledger_events (idempotency_key)
    WHERE event_type IN ('SETTLED_FINAL', 'RECONCILED_LATE_SETTLE');
