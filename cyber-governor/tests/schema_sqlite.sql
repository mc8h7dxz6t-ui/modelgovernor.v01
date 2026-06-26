-- SQLite schema for spine integration tests

CREATE TABLE principal_budgets (
    account_id VARCHAR(255) NOT NULL,
    ledger_type VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    balance NUMERIC(24, 12) NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT 1,
    lock_reason VARCHAR(255),
    locked_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, ledger_type, currency)
);

CREATE TABLE control_policy_registry (
    policy_id VARCHAR(255) PRIMARY KEY,
    instrument_type VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    risk_classification VARCHAR(20) NOT NULL,
    max_exposure_per_commit NUMERIC(24, 12) NOT NULL,
    commit_horizon_ms INT NOT NULL,
    allow_auto_expire BOOLEAN NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_to TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE platform_registry (
    platform_name VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    auth_token_hash VARCHAR(64) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE threat_crystals (
    crystal_id VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    risk_tier VARCHAR(20) NOT NULL,
    policy_id VARCHAR(255),
    facets TEXT NOT NULL DEFAULT '{}',
    request_fingerprint VARCHAR(64) NOT NULL,
    crystal_hash VARCHAR(64) NOT NULL,
    prev_crystal_hash VARCHAR(64),
    parent_crystal_id VARCHAR(255),
    horizon_expires_at TEXT NOT NULL,
    terminal_state VARCHAR(50),
    crystallized_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (platform, operation_id)
);

CREATE TABLE action_escrow_ledger (
    operation_id VARCHAR(255) PRIMARY KEY,
    crystal_id VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    reserved_exposure NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_exposure NUMERIC(24, 12) NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'CRYSTALLIZED',
    terminal_reason VARCHAR(255),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    committed_at TEXT,
    reconciled BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE security_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id VARCHAR(255) NOT NULL,
    crystal_id VARCHAR(255),
    account_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    exposure_delta NUMERIC(24, 12) NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}',
    prev_hash VARCHAR(64),
    row_hash VARCHAR(64) NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE action_budget_state (
    scope_key VARCHAR(512) PRIMARY KEY,
    cap_amount NUMERIC(24, 12) NOT NULL,
    reserved_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE threat_mesh_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_platform VARCHAR(50) NOT NULL,
    parent_facet_key VARCHAR(100) NOT NULL,
    parent_facet_value VARCHAR(255) NOT NULL,
    child_platform VARCHAR(50) NOT NULL,
    block_commit BOOLEAN NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT 1
);

INSERT INTO threat_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform)
VALUES ('identity_gate', 'session_state', 'STRANDED', 'egress_lock');

INSERT INTO control_policy_registry (
    policy_id, instrument_type, platform, jurisdiction, risk_classification,
    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES (
    'identity-critical-us', 'session', 'identity_gate', 'US', 'critical',
    1000000000, 30000, 0
);

INSERT INTO principal_budgets (account_id, ledger_type, currency, balance, active)
VALUES ('tenant-default', 'action_budget', 'USD', 100000000, 1);
