-- Phase 2 hardening: schema additions for per-trace spend caps,
-- missing updated_at column, and performance indexes.

-- updated_at was referenced in UPDATE statements since Phase 1 but was never
-- added to the DDL.  Adding it here so the schema and application code align.
ALTER TABLE escrow_ledger
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Per-trace spend cap.  Each model policy entry now carries a maximum total
-- spend that may be accumulated by a single trace_id across all reservations
-- and settlements.  The default of 50.000000 is a conservative institutional
-- ceiling; operators should tune this per model tier.
ALTER TABLE model_policy_registry
    ADD COLUMN IF NOT EXISTS max_cost_per_trace NUMERIC(18, 6) NOT NULL DEFAULT 50.000000;

UPDATE model_policy_registry
SET max_cost_per_trace = 50.000000
WHERE model_name IN ('gpt-4o-mini', 'gpt-4.1-mini');

-- Partial index optimised for the per-trace spend aggregation query executed
-- on every reserve call.  Covering user_id + trace_id with included amounts
-- avoids a heap fetch for the common case.
CREATE INDEX IF NOT EXISTS idx_escrow_trace_active_spend
ON escrow_ledger (user_id, trace_id)
INCLUDE (reserved_amount, actual_amount, status)
WHERE status IN ('RESERVED', 'SETTLED');
