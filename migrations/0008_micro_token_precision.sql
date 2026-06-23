-- Upgrade monetary columns to NUMERIC(24,12) for sub-micro-cent token pricing.
-- Example: gpt-4o-mini ≈ $0.00000015 per token remains representable.

ALTER TABLE user_wallets
    ALTER COLUMN balance TYPE NUMERIC(24, 12);

ALTER TABLE model_policy_registry
    ALTER COLUMN max_cost_per_request TYPE NUMERIC(24, 12),
    ALTER COLUMN fallback_price_per_token TYPE NUMERIC(24, 12);

ALTER TABLE escrow_ledger
    ALTER COLUMN reserved_amount TYPE NUMERIC(24, 12),
    ALTER COLUMN actual_amount TYPE NUMERIC(24, 12);

ALTER TABLE escrow_ledger
    ALTER COLUMN trace_cap_amount TYPE NUMERIC(24, 12),
    ALTER COLUMN drift_amount TYPE NUMERIC(24, 12);

ALTER TABLE ledger_events
    ALTER COLUMN amount_delta TYPE NUMERIC(24, 12);

ALTER TABLE trace_budget_state
    ALTER COLUMN cap_amount TYPE NUMERIC(24, 12),
    ALTER COLUMN reserved_total TYPE NUMERIC(24, 12),
    ALTER COLUMN settled_total TYPE NUMERIC(24, 12);

-- Attribution tables (no-op when table absent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = 'budget_scope_state'
    ) THEN
        ALTER TABLE budget_scope_state
            ALTER COLUMN cap_amount TYPE NUMERIC(24, 12),
            ALTER COLUMN consumed_amount TYPE NUMERIC(24, 12);
    END IF;
END $$;
