-- SQLite schema for spine integration tests

CREATE TABLE account_ledgers (
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

CREATE TABLE instrument_policy_registry (
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
    registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    base_url VARCHAR(512),
    default_policy_id VARCHAR(255),
    default_risk_tier VARCHAR(20) NOT NULL DEFAULT 'high',
    facet_schema TEXT NOT NULL DEFAULT '{}',
    invariant_counters TEXT NOT NULL DEFAULT '[]'
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

CREATE TABLE commit_escrow_ledger (
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

CREATE TABLE decision_events (
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

CREATE TABLE exposure_budget_state (
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

INSERT INTO instrument_policy_registry (
    policy_id, instrument_type, platform, jurisdiction, risk_classification,
    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES (
    'wire-critical-us', 'wire', 'wire_match', 'US', 'critical',
    1000000000, 30000, 0
);

INSERT INTO instrument_policy_registry (
    policy_id, instrument_type, platform, jurisdiction, risk_classification,
    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES (
    'credit-high-us', 'credit', 'credit_govern', 'US', 'high',
    250000, 300000, 0
);

INSERT INTO instrument_policy_registry (
    policy_id, instrument_type, platform, jurisdiction, risk_classification,
    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES (
    'algo-critical-us', 'algo', 'algofreeze', 'US', 'critical',
    1000000000, 5000, 0
);

INSERT INTO platform_registry (
    platform_name, display_name, auth_token_hash, enabled,
    base_url, default_policy_id, default_risk_tier, facet_schema, invariant_counters
) VALUES
    ('wire_match', 'WireMatch', 'builtin', 1, 'http://localhost:8093', 'wire-critical-us', 'critical', '{"required":["amount"]}', '[]'),
    ('algofreeze', 'AlgoFreeze', 'builtin', 1, 'http://localhost:8094', 'algo-critical-us', 'critical', '{"required":["runtime_sha"]}', '[]'),
    ('subledger_sync', 'SubledgerSync', 'builtin', 1, 'http://localhost:8095', NULL, 'high', '{"required":["entity_id","amount","currency"]}', '[]'),
    ('asset_ledger', 'AssetLedger', 'builtin', 1, 'http://localhost:8096', NULL, 'high', '{"required":["asset_id"]}', '[]'),
    ('credit_govern', 'CreditGovern', 'builtin', 1, 'http://localhost:8097', 'credit-high-us', 'high', '{"required":["application_id","exposure_amount","model_version_id"]}', '[]');

INSERT INTO account_ledgers (account_id, ledger_type, currency, balance, active)
VALUES ('desk-default', 'exposure', 'USD', 100000000, 1);

INSERT INTO crystal_mesh_rules (
    parent_platform, parent_facet_key, parent_facet_value, child_platform, block_commit, enabled
) VALUES ('algofreeze', 'freeze_state', 'FROZEN', 'wire_match', 1, 1);

CREATE TABLE admin_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_subject VARCHAR(255) NOT NULL,
    actor_method VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(255),
    metadata TEXT NOT NULL DEFAULT '{}',
    prev_hash VARCHAR(64),
    row_hash VARCHAR(64),
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE decision_chain_anchors (
    anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    head_hash VARCHAR(64) NOT NULL UNIQUE,
    sealed_count INT NOT NULL,
    total_events INT NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'api',
    anchored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guardrail_incidents (
    incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id VARCHAR(255),
    crystal_id VARCHAR(255),
    incident_type VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE platform_action_attempts (
    attempt_key VARCHAR(255) PRIMARY KEY,
    operation_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    attempt_status VARCHAR(50) NOT NULL,
    external_ref VARCHAR(255),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE platform_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subledger_transactions (
    txn_hash VARCHAR(64) PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    counterparty_id VARCHAR(255) NOT NULL,
    amount NUMERIC(24, 12) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    value_date VARCHAR(20) NOT NULL,
    reference TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    fx_hash VARCHAR(64),
    mirror_hash VARCHAR(64),
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE asset_ledger_assets (
    asset_id VARCHAR(255) PRIMARY KEY,
    description TEXT NOT NULL,
    acquisition_cost NUMERIC(24, 12) NOT NULL,
    book_value NUMERIC(24, 12) NOT NULL,
    accumulated_depreciation NUMERIC(24, 12) NOT NULL DEFAULT 0,
    method VARCHAR(50) NOT NULL DEFAULT 'straight_line',
    jurisdiction VARCHAR(10) NOT NULL DEFAULT 'US',
    useful_life_months INT NOT NULL DEFAULT 60,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE asset_depreciation_charges (
    asset_id VARCHAR(255) NOT NULL,
    period VARCHAR(20) NOT NULL,
    charge NUMERIC(24, 12) NOT NULL,
    reg_table_version VARCHAR(50),
    crystal_id VARCHAR(255),
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_id, period)
);

CREATE TABLE credit_evaluations (
    application_id VARCHAR(255) PRIMARY KEY,
    decision VARCHAR(20) NOT NULL,
    exposure_amount NUMERIC(24, 12) NOT NULL,
    model_version_id VARCHAR(100) NOT NULL,
    desk_id VARCHAR(255) NOT NULL,
    score NUMERIC(10, 6),
    explanation_id VARCHAR(255),
    crystal_id VARCHAR(255),
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
