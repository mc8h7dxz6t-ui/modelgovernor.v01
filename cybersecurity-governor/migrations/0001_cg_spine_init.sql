-- Cybersecurity Governor Spine — initial schema (CCP-native control plane)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE security_budget_ledgers (
    account_id VARCHAR(255) NOT NULL,
    ledger_type VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    balance NUMERIC(24, 12) NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    lock_reason VARCHAR(255),
    locked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, ledger_type, currency),
    CONSTRAINT cg_reserve_nonnegative CHECK (balance >= 0)
);

CREATE TABLE security_policy_registry (
    policy_id VARCHAR(255) PRIMARY KEY,
    line_of_business VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    risk_classification VARCHAR(20) NOT NULL,
    max_budget_per_commit NUMERIC(24, 12) NOT NULL,
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
    policy_id VARCHAR(255) REFERENCES security_policy_registry(policy_id),
    facets JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_fingerprint VARCHAR(64) NOT NULL,
    crystal_hash VARCHAR(64) NOT NULL,
    prev_crystal_hash VARCHAR(64),
    parent_crystal_id VARCHAR(255),
    horizon_expires_at TIMESTAMPTZ NOT NULL,
    terminal_state VARCHAR(50),
    crystallized_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT cg_crystal_unique_op UNIQUE (platform, operation_id)
);

CREATE INDEX idx_cg_crystals_horizon_sweep
ON governance_crystals (terminal_state, horizon_expires_at)
WHERE terminal_state IS NULL;

CREATE TYPE security_action_status AS ENUM (
    'CRYSTALLIZED',
    'IN_FLIGHT',
    'ACTION_TIMEOUT',
    'COMMITTED',
    'EXPIRED',
    'STRANDED',
    'ADJUDICATED'
);

CREATE TABLE security_escrow_ledger (
    operation_id VARCHAR(255) PRIMARY KEY,
    crystal_id VARCHAR(255) NOT NULL REFERENCES governance_crystals(crystal_id),
    account_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    reserved_budget NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_budget NUMERIC(24, 12) NOT NULL DEFAULT 0,
    status security_action_status NOT NULL DEFAULT 'CRYSTALLIZED',
    terminal_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    committed_at TIMESTAMPTZ,
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT cg_escrow_nonnegative_reserved CHECK (reserved_budget >= 0),
    CONSTRAINT cg_escrow_nonnegative_committed CHECK (committed_budget >= 0)
);

CREATE INDEX idx_cg_escrow_sweep
ON security_escrow_ledger (status, expires_at)
WHERE status IN ('CRYSTALLIZED', 'IN_FLIGHT', 'ACTION_TIMEOUT');

CREATE TABLE security_events (
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

CREATE INDEX idx_cg_security_events_trail
ON security_events (operation_id, recorded_at);

CREATE TABLE aggregate_limit_state (
    scope_key VARCHAR(512) PRIMARY KEY,
    cap_amount NUMERIC(24, 12) NOT NULL,
    reserved_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT cg_aggregate_cap_nonnegative CHECK (cap_amount >= 0),
    CONSTRAINT cg_aggregate_reserved_within_cap CHECK (reserved_total <= cap_amount)
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

INSERT INTO security_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_budget_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('egress-critical-us', 'network', 'egress_govern', 'US', 'critical', 1000000.000000000000, 15000, FALSE),
    ('compliance-standard-us', 'audit', 'compliance_logger', 'US', 'high', 100000.000000000000, 600000, FALSE);

INSERT INTO security_budget_ledgers (account_id, ledger_type, currency, balance)
VALUES ('tenant-default', 'case', 'USD', 100000000.000000000000);
