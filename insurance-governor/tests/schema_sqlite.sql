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
    manifest_json TEXT NOT NULL DEFAULT '{}',
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
), (
    'bind-standard-us', 'commercial', 'bind_authority', 'US', 'high',
    2500000, 600000, 0
), (
    'parametric-cat-us', 'property', 'parametric_oracle', 'US', 'critical',
    10000000, 60000, 0
), (
    'zk-audit-us', 'casualty', 'zk_claim_audit', 'US', 'critical',
    1000000, 300000, 0
), (
    'spatial-property-us', 'property', 'spatial_twin', 'US', 'high',
    5000000, 300000, 0
), (
    'ev-battery-us', 'auto', 'battery_liability', 'US', 'critical',
    2500000, 300000, 0
), (
    'subrogation-us', 'casualty', 'subrogation_graph', 'US', 'high',
    3000000, 600000, 0
);

INSERT INTO reserve_ledgers (account_id, ledger_type, currency, balance, active)
VALUES ('carrier-default', 'case', 'USD', 100000000, 1);

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled, manifest_json)
VALUES
  ('claim_gate', 'ClaimGate', 'dev-claim-gate-hash', 1, '{"required_facet_keys":["claim_id"],"commit_decisions":["APPROVED"]}'),
  ('bind_authority', 'BindAuthority', 'dev-bind-authority-hash', 1, '{"required_facet_keys":["application_id"],"commit_decisions":["BOUND"]}'),
  ('parametric_oracle', 'ParametricOracle', 'dev-parametric-oracle-hash', 1, '{"required_facet_keys":["event_id","oracle_attestation_hash"],"commit_decisions":["TRIGGERED"]}'),
  ('zk_claim_audit', 'ZkClaimAudit', 'dev-zk-claim-audit-hash', 1, '{"required_facet_keys":["claim_id","commitment_hash"],"commit_decisions":["SEALED","VERIFIED"]}'),
  ('spatial_twin', 'SpatialTwin', 'dev-spatial-twin-hash', 1, '{"required_facet_keys":["claim_id","point_cloud_hash"],"commit_decisions":["APPROVED"]}'),
  ('battery_liability', 'BatteryLiability', 'dev-battery-liability-hash', 1, '{"required_facet_keys":["claim_id"],"commit_decisions":["APPROVED"]}'),
  ('subrogation_graph', 'SubrogationGraph', 'dev-subrogation-graph-hash', 1, '{"required_facet_keys":["claim_id"],"commit_decisions":["RECOVERY_APPROVED"]}');

CREATE TABLE claim_chain_anchors (
    anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    head_hash CHAR(64) NOT NULL,
    sealed_count INTEGER NOT NULL,
    total_events INTEGER NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'cronjob',
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX claim_chain_anchors_one_per_head ON claim_chain_anchors (head_hash);

CREATE TABLE admin_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_subject TEXT NOT NULL,
    actor_method VARCHAR(32) NOT NULL,
    actor_roles TEXT,
    action VARCHAR(128) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    prev_hash CHAR(64),
    row_hash CHAR(64),
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
