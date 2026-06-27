-- Insurance Governor Spine — initial schema (CCP-native control plane)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE reserve_ledgers (
    account_id VARCHAR(255) NOT NULL,
    ledger_type VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    balance NUMERIC(24, 12) NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    lock_reason VARCHAR(255),
    locked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, ledger_type, currency),
    CONSTRAINT ig_reserve_nonnegative CHECK (balance >= 0)
);

CREATE TABLE coverage_policy_registry (
    policy_id VARCHAR(255) PRIMARY KEY,
    line_of_business VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    risk_classification VARCHAR(20) NOT NULL,
    max_reserve_per_commit NUMERIC(24, 12) NOT NULL,
    commit_horizon_ms INT NOT NULL,
    allow_auto_expire BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_to TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE platform_registry (
    platform_name VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    auth_token_hash VARCHAR(64) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE governance_crystals (
    crystal_id VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    risk_tier VARCHAR(20) NOT NULL,
    policy_id VARCHAR(255) REFERENCES coverage_policy_registry(policy_id),
    facets JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_fingerprint VARCHAR(64) NOT NULL,
    crystal_hash VARCHAR(64) NOT NULL,
    prev_crystal_hash VARCHAR(64),
    parent_crystal_id VARCHAR(255),
    horizon_expires_at TIMESTAMPTZ NOT NULL,
    terminal_state VARCHAR(50),
    crystallized_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ig_crystal_unique_op UNIQUE (platform, operation_id)
);

CREATE INDEX idx_ig_crystals_horizon_sweep
ON governance_crystals (terminal_state, horizon_expires_at)
WHERE terminal_state IS NULL;

CREATE TYPE claim_status AS ENUM (
    'CRYSTALLIZED',
    'IN_FLIGHT',
    'ACTION_TIMEOUT',
    'COMMITTED',
    'EXPIRED',
    'STRANDED',
    'ADJUDICATED'
);

CREATE TABLE claim_escrow_ledger (
    operation_id VARCHAR(255) PRIMARY KEY,
    crystal_id VARCHAR(255) NOT NULL REFERENCES governance_crystals(crystal_id),
    account_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    reserved_reserve NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_reserve NUMERIC(24, 12) NOT NULL DEFAULT 0,
    status claim_status NOT NULL DEFAULT 'CRYSTALLIZED',
    terminal_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    committed_at TIMESTAMPTZ,
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT ig_escrow_nonnegative_reserved CHECK (reserved_reserve >= 0),
    CONSTRAINT ig_escrow_nonnegative_committed CHECK (committed_reserve >= 0)
);

CREATE INDEX idx_ig_escrow_sweep
ON claim_escrow_ledger (status, expires_at)
WHERE status IN ('CRYSTALLIZED', 'IN_FLIGHT', 'ACTION_TIMEOUT');

CREATE TABLE claim_events (
    event_id BIGSERIAL PRIMARY KEY,
    operation_id VARCHAR(255) NOT NULL,
    crystal_id VARCHAR(255),
    account_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    reserve_delta NUMERIC(24, 12) NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash VARCHAR(64),
    row_hash VARCHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ig_claim_events_trail
ON claim_events (operation_id, recorded_at);

CREATE TABLE aggregate_limit_state (
    scope_key VARCHAR(512) PRIMARY KEY,
    cap_amount NUMERIC(24, 12) NOT NULL,
    reserved_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ig_aggregate_cap_nonnegative CHECK (cap_amount >= 0),
    CONSTRAINT ig_aggregate_reserved_within_cap CHECK (reserved_total <= cap_amount)
);

CREATE TABLE crystal_mesh_rules (
    rule_id SERIAL PRIMARY KEY,
    parent_platform VARCHAR(50) NOT NULL,
    parent_facet_key VARCHAR(100) NOT NULL,
    parent_facet_value VARCHAR(255) NOT NULL,
    child_platform VARCHAR(50) NOT NULL,
    block_commit BOOLEAN NOT NULL DEFAULT TRUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE guardrail_incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    operation_id VARCHAR(255),
    crystal_id VARCHAR(255),
    incident_type VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO coverage_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_reserve_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('claim-high-us', 'casualty', 'claim_gate', 'US', 'high', 5000000.000000000000, 300000, FALSE),
    ('claim-critical-us', 'casualty', 'claim_gate', 'US', 'critical', 10000000.000000000000, 30000, FALSE);

INSERT INTO reserve_ledgers (account_id, ledger_type, currency, balance)
VALUES ('carrier-default', 'case', 'USD', 100000000.000000000000);
