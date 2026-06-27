-- SQLite schema for Cybersecurity Governor spine integration tests

CREATE TABLE security_budget_ledgers (
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

CREATE TABLE security_policy_registry (
    policy_id VARCHAR(255) PRIMARY KEY,
    line_of_business VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    risk_classification VARCHAR(20) NOT NULL,
    max_budget_per_commit NUMERIC(24, 12) NOT NULL,
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

CREATE TABLE security_escrow_ledger (
    operation_id VARCHAR(255) PRIMARY KEY,
    crystal_id VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    reserved_budget NUMERIC(24, 12) NOT NULL DEFAULT 0,
    committed_budget NUMERIC(24, 12) NOT NULL DEFAULT 0,
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

INSERT INTO security_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_budget_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('egress-critical-us', 'network', 'egress_govern', 'US', 'critical', 1000000, 15000, 0),
    ('identity-high-us', 'iam', 'identity_govern', 'US', 'high', 500000, 60000, 0),
    ('threat-critical-us', 'detection', 'threat_proxy', 'US', 'critical', 2000000, 10000, 0),
    ('ir-critical-us', 'response', 'incident_response_gate', 'US', 'critical', 5000000, 30000, 0),
    ('posture-high-us', 'vuln', 'posture_reconcile', 'US', 'high', 10000000, 300000, 0),
    ('compliance-standard-us', 'audit', 'compliance_logger', 'US', 'high', 100000, 600000, 0),
    ('witness-standard-us', 'telemetry', 'witness_bridge', 'US', 'standard', 100000, 3600000, 1),
    ('lineage-critical-us', 'lineage', 'lineage_ingest', 'US', 'critical', 500000, 60000, 0),
    ('content-high-us', 'dlp', 'content_guard', 'US', 'high', 250000, 120000, 0);

INSERT INTO security_budget_ledgers (account_id, ledger_type, currency, balance, active)
VALUES ('tenant-default', 'case', 'USD', 100000000, 1);

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled, manifest_json)
VALUES
  ('egress_govern', 'EgressGovern', 'dev-egress-govern-hash', 1, '{"required_facet_keys":["flow_id","destination_host","egress_decision"],"commit_decisions":["ALLOWED"]}'),
  ('identity_govern', 'IdentityGovern', 'dev-identity-govern-hash', 1, '{"required_facet_keys":["principal","workload_sa","identity_decision"],"commit_decisions":["VERIFIED"]}'),
  ('threat_proxy', 'ThreatProxy', 'dev-threat-proxy-hash', 1, '{"required_facet_keys":["request_id","threat_score","threat_decision"],"commit_decisions":["CLEARED"]}'),
  ('incident_response_gate', 'IncidentResponseGate', 'dev-ir-gate-hash', 1, '{"required_facet_keys":["incident_id","action_type","ir_decision"],"commit_decisions":["AUTHORIZED"]}'),
  ('posture_reconcile', 'PostureReconcile', 'dev-posture-reconcile-hash', 1, '{"required_facet_keys":["asset_id","match_state"],"commit_decisions":["MATCHED"]}'),
  ('compliance_logger', 'ComplianceLogger', 'dev-compliance-logger-hash', 1, '{"required_facet_keys":["framework","control_id","evidence_hash"],"commit_decisions":["LOGGED"]}'),
  ('witness_bridge', 'WitnessBridge', 'dev-witness-bridge-hash', 1, '{"required_facet_keys":["source","event_type","witness_decision"],"commit_decisions":["WITNESSED"]}'),
  ('lineage_ingest', 'LineageIngest', 'dev-lineage-ingest-hash', 1, '{"required_facet_keys":["source_system","edge_type","lineage_decision"],"commit_decisions":["CRITICAL"]}'),
  ('content_guard', 'ContentGuard', 'dev-content-guard-hash', 1, '{"required_facet_keys":["content_decision","principal_id"],"commit_decisions":["ALLOWED","REDACTED"]}');

INSERT INTO crystal_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform, block_commit, enabled)
VALUES
  ('posture_reconcile', 'match_state', 'DRIFT', 'egress_govern', 1, 1),
  ('posture_reconcile', 'match_state', 'DRIFT', 'incident_response_gate', 1, 1),
  ('threat_proxy', 'threat_decision', 'BLOCKED', 'egress_govern', 1, 1),
  ('threat_proxy', 'threat_decision', 'BLOCKED', 'incident_response_gate', 1, 1),
  ('identity_govern', 'identity_decision', 'VIOLATION', 'incident_response_gate', 1, 1),
  ('identity_govern', 'identity_decision', 'VIOLATION', 'egress_govern', 1, 1),
  ('egress_govern', 'egress_decision', 'DENIED', 'incident_response_gate', 1, 1),
  ('content_guard', 'content_decision', 'BLOCKED', 'egress_govern', 1, 1),
  ('content_guard', 'content_decision', 'BLOCKED', 'incident_response_gate', 1, 1),
  ('lineage_ingest', 'lineage_decision', 'CRITICAL', 'egress_govern', 1, 1);

CREATE TABLE lineage_edges (
    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    parent_ref TEXT,
    child_ref TEXT NOT NULL,
    principal_id TEXT,
    physical_time TEXT NOT NULL,
    logical_counter INTEGER NOT NULL DEFAULT 0,
    causal_parent_ids TEXT NOT NULL DEFAULT '[]',
    severity TEXT NOT NULL DEFAULT 'standard',
    metadata TEXT NOT NULL DEFAULT '{}',
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security_chain_anchors (
    anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    head_hash CHAR(64) NOT NULL,
    sealed_count INTEGER NOT NULL,
    total_events INTEGER NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'cronjob',
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX security_chain_anchors_one_per_head ON security_chain_anchors (head_hash);

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

CREATE TABLE security_action_idempotency (
    idempotency_key VARCHAR(512) PRIMARY KEY,
    action_id VARCHAR(255) NOT NULL,
    platform VARCHAR(64) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    reference TEXT,
    crystal_id VARCHAR(255),
    external_ref VARCHAR(255),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE siem_export_cache (
    export_key VARCHAR(255) PRIMARY KEY,
    framework VARCHAR(64) NOT NULL,
    control_id VARCHAR(128) NOT NULL,
    payload TEXT NOT NULL,
    evidence_hash CHAR(64) NOT NULL,
    exported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
