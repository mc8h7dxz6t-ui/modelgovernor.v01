CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- PostgreSQL is the sole financial source of truth for wallet balances and ledger lifecycle state.

CREATE TABLE IF NOT EXISTS wallets (
    wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    wallet_ref TEXT NOT NULL,
    currency_code TEXT NOT NULL DEFAULT 'USD',
    balance_available NUMERIC(20, 6) NOT NULL DEFAULT 0,
    balance_reserved NUMERIC(20, 6) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT wallets_balance_available_non_negative CHECK (balance_available >= 0),
    CONSTRAINT wallets_balance_reserved_non_negative CHECK (balance_reserved >= 0),
    CONSTRAINT wallets_currency_code_format CHECK (currency_code ~ '^[A-Z]{3}$'),
    CONSTRAINT wallets_tenant_wallet_unique UNIQUE (tenant_id, wallet_ref)
);

CREATE INDEX IF NOT EXISTS idx_wallets_tenant_lookup ON wallets (tenant_id, wallet_ref);

CREATE TABLE IF NOT EXISTS model_policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    max_input_tokens INTEGER NOT NULL,
    max_output_tokens INTEGER NOT NULL,
    max_cost_per_request NUMERIC(20, 6) NOT NULL,
    stream_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    fallback_price_per_token NUMERIC(20, 8) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT model_policies_cost_non_negative CHECK (max_cost_per_request >= 0),
    CONSTRAINT model_policies_fallback_price_non_negative CHECK (fallback_price_per_token >= 0),
    CONSTRAINT model_policies_max_input_positive CHECK (max_input_tokens > 0),
    CONSTRAINT model_policies_max_output_positive CHECK (max_output_tokens > 0),
    CONSTRAINT model_policies_unique_per_tenant_model UNIQUE (tenant_id, provider, model_name)
);

CREATE INDEX IF NOT EXISTS idx_model_policies_lookup ON model_policies (tenant_id, provider, model_name);

CREATE TYPE ledger_entry_status AS ENUM ('RESERVED', 'SETTLED', 'EXPIRED', 'REVERSED', 'CANCELLED');

CREATE TABLE IF NOT EXISTS ledger_entries (
    ledger_entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES wallets(wallet_id),
    policy_id UUID REFERENCES model_policies(policy_id),
    request_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    reservation_status ledger_entry_status NOT NULL DEFAULT 'RESERVED',
    amount_reserved NUMERIC(20, 6) NOT NULL,
    amount_settled NUMERIC(20, 6) NOT NULL DEFAULT 0,
    amount_released NUMERIC(20, 6) NOT NULL DEFAULT 0,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reserved_until TIMESTAMPTZ,
    settled_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ledger_entries_amount_reserved_non_negative CHECK (amount_reserved >= 0),
    CONSTRAINT ledger_entries_amount_settled_non_negative CHECK (amount_settled >= 0),
    CONSTRAINT ledger_entries_amount_released_non_negative CHECK (amount_released >= 0),
    CONSTRAINT ledger_entries_amount_accounting_consistent CHECK (amount_settled + amount_released <= amount_reserved),
    CONSTRAINT ledger_entries_reserved_requires_expiry CHECK (
        reservation_status <> 'RESERVED' OR reserved_until IS NOT NULL
    ),
    CONSTRAINT ledger_entries_settlement_timestamp_when_settled CHECK (
        reservation_status <> 'SETTLED' OR settled_at IS NOT NULL
    ),
    CONSTRAINT ledger_entries_wallet_request_idempotency UNIQUE (wallet_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_wallet_status ON ledger_entries (wallet_id, reservation_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_expiry_sweep ON ledger_entries (reserved_until) WHERE reservation_status = 'RESERVED';
CREATE INDEX IF NOT EXISTS idx_ledger_entries_request_lookup ON ledger_entries (request_id);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ledger_entry_id UUID NOT NULL REFERENCES ledger_entries(ledger_entry_id),
    wallet_id UUID NOT NULL REFERENCES wallets(wallet_id),
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_ledger_join ON audit_events (ledger_entry_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_wallet_join ON audit_events (wallet_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_type_time ON audit_events (event_type, occurred_at DESC);
