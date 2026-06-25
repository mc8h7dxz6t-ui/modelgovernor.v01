-- SQLite schema for Insurance Governor spine integration tests

CREATE TABLE reserve_ledgers (
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

CREATE TABLE coverage_policy_registry (
    policy_id VARCHAR(255) PRIMARY KEY,
    line_of_business VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    risk_classification VARCHAR(20) NOT NULL,
    max_reserve_per_commit NUMERIC(24, 12) NOT NULL,
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

CREATE TABLE governance_crystals (
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

CREATE TABLE claim_escrow_ledger (
    operation_id VARCHAR(255) PRIMARY KEY,
    crystal_id VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    reserved_reserve NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_reserve NUMERIC(24, 12) NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'CRYSTALLIZED',
    terminal_reason VARCHAR(255),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    committed_at TEXT,
    reconciled BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE claim_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id VARCHAR(255) NOT NULL,
    crystal_id VARCHAR(255),
    account_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    reserve_delta NUMERIC(24, 12) NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}',
    prev_hash VARCHAR(64),
    row_hash VARCHAR(64) NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE aggregate_limit_state (
    scope_key VARCHAR(512) PRIMARY KEY,
    cap_amount NUMERIC(24, 12) NOT NULL,
    reserved_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crystal_mesh_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_platform VARCHAR(50) NOT NULL,
    parent_facet_key VARCHAR(100) NOT NULL,
    parent_facet_value VARCHAR(255) NOT NULL,
    child_platform VARCHAR(50) NOT NULL,
    block_commit BOOLEAN NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT 1
);

INSERT INTO coverage_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_reserve_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES (
    'claim-high-us', 'casualty', 'claim_gate', 'US', 'high',
    5000000, 300000, 0
);

INSERT INTO reserve_ledgers (account_id, ledger_type, currency, balance, active)
VALUES ('carrier-default', 'case', 'USD', 100000000, 1);
