ALTER TABLE user_wallets
DROP CONSTRAINT IF EXISTS user_wallets_nonnegative_balance;

ALTER TABLE user_wallets
ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS lock_reason VARCHAR(255);

ALTER TYPE escrow_status ADD VALUE IF NOT EXISTS 'IN_FLIGHT';
ALTER TYPE escrow_status ADD VALUE IF NOT EXISTS 'PROVIDER_TIMEOUT';
ALTER TYPE escrow_status ADD VALUE IF NOT EXISTS 'STRANDED';

ALTER TABLE escrow_ledger
DROP CONSTRAINT IF EXISTS escrow_status_timestamp_consistency;

ALTER TABLE escrow_ledger
ADD COLUMN IF NOT EXISTS trace_cap_amount NUMERIC(18, 6) NOT NULL DEFAULT 25.000000,
ADD COLUMN IF NOT EXISTS dispatch_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS drift_amount NUMERIC(18, 6) NOT NULL DEFAULT 0.000000;

ALTER TABLE escrow_ledger
ADD CONSTRAINT escrow_status_timestamp_consistency CHECK (
    (status = 'RESERVED' AND settled_at IS NULL AND expired_at IS NULL)
    OR
    (status = 'IN_FLIGHT' AND dispatch_started_at IS NOT NULL AND settled_at IS NULL)
    OR
    (status = 'PROVIDER_TIMEOUT' AND dispatch_started_at IS NOT NULL AND settled_at IS NULL)
    OR
    (status = 'STRANDED' AND dispatch_started_at IS NOT NULL AND expired_at IS NOT NULL)
    OR
    (status = 'SETTLED' AND settled_at IS NOT NULL)
    OR
    (status = 'EXPIRED' AND expired_at IS NOT NULL AND settled_at IS NULL)
    OR
    (status = 'REFUNDED')
);

CREATE TABLE IF NOT EXISTS trace_budget_state (
    trace_id VARCHAR(255) PRIMARY KEY,
    cap_amount NUMERIC(18, 6) NOT NULL,
    reserved_total NUMERIC(18, 6) NOT NULL DEFAULT 0.000000,
    settled_total NUMERIC(18, 6) NOT NULL DEFAULT 0.000000,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT trace_budget_state_nonnegative_reserved CHECK (reserved_total >= 0),
    CONSTRAINT trace_budget_state_nonnegative_settled CHECK (settled_total >= 0)
);

CREATE TABLE IF NOT EXISTS provider_dispatch_attempts (
    attempt_key VARCHAR(255) PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL REFERENCES escrow_ledger(idempotency_key),
    provider_name VARCHAR(255),
    model_name VARCHAR(255),
    provider_request_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    terminal_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT provider_dispatch_attempts_status_valid CHECK (
        status IN ('IN_FLIGHT', 'PROVIDER_TIMEOUT', 'SETTLED')
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_provider_dispatch_attempts_provider_request_id
ON provider_dispatch_attempts (provider_request_id)
WHERE provider_request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_provider_dispatch_attempts_operation
ON provider_dispatch_attempts (idempotency_key, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_trace_budget_state_updated_at
ON trace_budget_state (updated_at DESC);
