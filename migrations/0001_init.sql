CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE user_wallets (
    user_id VARCHAR(255) PRIMARY KEY,
    balance NUMERIC(18, 6) NOT NULL DEFAULT 100.000000,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TYPE escrow_status AS ENUM ('RESERVED', 'SETTLED', 'EXPIRED', 'REFUNDED');

CREATE TABLE model_policy_registry (
    model_name VARCHAR(255) PRIMARY KEY,
    provider VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    max_input_tokens INT NOT NULL,
    max_output_tokens INT NOT NULL,
    max_cost_per_request NUMERIC(18, 6) NOT NULL,
    stream_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    fallback_price_per_token NUMERIC(18, 6) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE escrow_ledger (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES user_wallets(user_id),
    trace_id VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL REFERENCES model_policy_registry(model_name),
    request_fingerprint VARCHAR(64) NOT NULL,
    reserved_amount NUMERIC(18, 6) NOT NULL,
    actual_amount NUMERIC(18, 6) NOT NULL DEFAULT 0.000000,
    status escrow_status NOT NULL DEFAULT 'RESERVED',
    provider_request_id VARCHAR(255),
    terminal_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    settled_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT escrow_nonnegative_reserved CHECK (reserved_amount >= 0),
    CONSTRAINT escrow_nonnegative_actual CHECK (actual_amount >= 0)
);

CREATE TABLE ledger_events (
    event_id BIGSERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    amount_delta NUMERIC(18, 6) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_escrow_reconciliation_sweep
ON escrow_ledger (status, expires_at)
INCLUDE (idempotency_key, user_id, reserved_amount)
WHERE status = 'RESERVED';

CREATE INDEX idx_ledger_events_audit_trail
ON ledger_events (idempotency_key, recorded_at);
