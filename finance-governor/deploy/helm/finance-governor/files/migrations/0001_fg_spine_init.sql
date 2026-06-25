-- Finance Governor Spine — initial schema
-- CCP-native control plane (parallel to ModelGovernor migrations)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Account ledgers ───────────────────────────────────────────────────────

CREATE TABLE account_ledgers (
    account_id VARCHAR(255) NOT NULL,
    ledger_type VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    balance NUMERIC(24, 12) NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    lock_reason VARCHAR(255),
    locked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, ledger_type, currency),
    CONSTRAINT fg_account_nonnegative CHECK (balance >= 0)
);

-- ─── Instrument policy (finance-adapted model_policy_registry) ─────────────

CREATE TABLE instrument_policy_registry (
    policy_id VARCHAR(255) PRIMARY KEY,
    instrument_type VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    risk_classification VARCHAR(20) NOT NULL,
    max_exposure_per_commit NUMERIC(24, 12) NOT NULL,
    commit_horizon_ms INT NOT NULL,
    allow_auto_expire BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_to TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ─── Platform registry (spine knows connected platforms) ───────────────────

CREATE TABLE platform_registry (
    platform_name VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    auth_token_hash VARCHAR(64) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ─── Governance crystals (CCP core) ────────────────────────────────────────

CREATE TABLE governance_crystals (
    crystal_id VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    risk_tier VARCHAR(20) NOT NULL,
    policy_id VARCHAR(255) REFERENCES instrument_policy_registry(policy_id),
    facets JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_fingerprint VARCHAR(64) NOT NULL,
    crystal_hash VARCHAR(64) NOT NULL,
    prev_crystal_hash VARCHAR(64),
    parent_crystal_id VARCHAR(255),
    horizon_expires_at TIMESTAMPTZ NOT NULL,
    terminal_state VARCHAR(50),
    crystallized_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fg_crystal_unique_op UNIQUE (platform, operation_id)
);

CREATE INDEX idx_fg_crystals_horizon_sweep
ON governance_crystals (terminal_state, horizon_expires_at)
WHERE terminal_state IS NULL;

CREATE INDEX idx_fg_crystals_chain
ON governance_crystals (crystallized_at, crystal_id);

-- ─── Commit escrow (finance-adapted escrow_ledger) ─────────────────────────

CREATE TYPE commit_status AS ENUM (
    'CRYSTALLIZED',
    'IN_FLIGHT',
    'ACTION_TIMEOUT',
    'COMMITTED',
    'EXPIRED',
    'STRANDED',
    'ADJUDICATED'
);

CREATE TABLE commit_escrow_ledger (
    operation_id VARCHAR(255) PRIMARY KEY,
    crystal_id VARCHAR(255) NOT NULL REFERENCES governance_crystals(crystal_id),
    account_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    reserved_exposure NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_exposure NUMERIC(24, 12) NOT NULL DEFAULT 0,
    status commit_status NOT NULL DEFAULT 'CRYSTALLIZED',
    terminal_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    committed_at TIMESTAMPTZ,
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fg_escrow_nonnegative_reserved CHECK (reserved_exposure >= 0),
    CONSTRAINT fg_escrow_nonnegative_committed CHECK (committed_exposure >= 0)
);

CREATE INDEX idx_fg_escrow_sweep
ON commit_escrow_ledger (status, expires_at)
WHERE status IN ('CRYSTALLIZED', 'IN_FLIGHT', 'ACTION_TIMEOUT');

-- ─── Decision events (finance-adapted ledger_events) ───────────────────────

CREATE TABLE decision_events (
    event_id BIGSERIAL PRIMARY KEY,
    operation_id VARCHAR(255) NOT NULL,
    crystal_id VARCHAR(255),
    account_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    exposure_delta NUMERIC(24, 12) NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash VARCHAR(64),
    row_hash VARCHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fg_decision_events_trail
ON decision_events (operation_id, recorded_at);

-- ─── Exposure budgets (finance-adapted trace_budget_state) ───────────────────

CREATE TABLE exposure_budget_state (
    scope_key VARCHAR(512) PRIMARY KEY,
    cap_amount NUMERIC(24, 12) NOT NULL,
    reserved_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fg_exposure_cap_nonnegative CHECK (cap_amount >= 0),
    CONSTRAINT fg_exposure_reserved_within_cap CHECK (reserved_total <= cap_amount)
);

-- ─── Crystal mesh rules (cross-platform spine) ─────────────────────────────

CREATE TABLE crystal_mesh_rules (
    rule_id SERIAL PRIMARY KEY,
    parent_platform VARCHAR(50) NOT NULL,
    parent_facet_key VARCHAR(100) NOT NULL,
    parent_facet_value VARCHAR(255) NOT NULL,
    child_platform VARCHAR(50) NOT NULL,
    block_commit BOOLEAN NOT NULL DEFAULT TRUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

-- ─── Platform action attempts ──────────────────────────────────────────────

CREATE TABLE platform_action_attempts (
    attempt_key VARCHAR(255) PRIMARY KEY,
    operation_id VARCHAR(255) NOT NULL REFERENCES commit_escrow_ledger(operation_id),
    platform VARCHAR(50) NOT NULL,
    attempt_status VARCHAR(50) NOT NULL,
    external_ref VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ─── Guardrail incidents ───────────────────────────────────────────────────

CREATE TABLE guardrail_incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    operation_id VARCHAR(255),
    crystal_id VARCHAR(255),
    incident_type VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ─── Seed: default mesh rule (algo freeze blocks wire) ─────────────────────

INSERT INTO crystal_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform)
VALUES ('algofreeze', 'freeze_state', 'FROZEN', 'wire_match');

INSERT INTO instrument_policy_registry (
    policy_id, instrument_type, platform, jurisdiction, risk_classification,
    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('wire-critical-us', 'wire', 'wire_match', 'US', 'critical', 1000000000.000000000000, 30000, FALSE),
    ('algo-critical-us', 'algo', 'algofreeze', 'US', 'critical', 1000000000.000000000000, 5000, FALSE),
    ('credit-high-us', 'credit', 'credit_govern', 'US', 'high', 250000.000000000000, 300000, FALSE);

INSERT INTO account_ledgers (account_id, ledger_type, currency, balance)
VALUES ('desk-default', 'exposure', 'USD', 100000000.000000000000);
