-- Sales SKU platforms + structural lineage DAG (gold-standard completion)

CREATE TABLE IF NOT EXISTS lineage_edges (
    edge_id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL,
    edge_type VARCHAR(50) NOT NULL,
    parent_ref VARCHAR(512),
    child_ref VARCHAR(512) NOT NULL,
    principal_id VARCHAR(255),
    physical_time TIMESTAMPTZ NOT NULL,
    logical_counter BIGINT NOT NULL DEFAULT 0,
    causal_parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity VARCHAR(20) NOT NULL DEFAULT 'standard',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lineage_edges_parent ON lineage_edges (parent_ref);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_child ON lineage_edges (child_ref);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_principal ON lineage_edges (principal_id, physical_time DESC);

INSERT INTO security_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_budget_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('witness-standard-us', 'telemetry', 'witness_bridge', 'US', 'standard', 100000.000000000000, 3600000, TRUE),
    ('lineage-critical-us', 'lineage', 'lineage_ingest', 'US', 'critical', 500000.000000000000, 60000, FALSE),
    ('content-high-us', 'dlp', 'content_guard', 'US', 'high', 250000.000000000000, 120000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled, manifest_json)
VALUES
    ('witness_bridge', 'WitnessBridge', 'dev-witness-bridge-hash', TRUE,
     '{"required_facet_keys":["source","event_type","witness_decision"],"commit_decisions":["WITNESSED"],"default_policy_id":"witness-standard-us","port":8129}'::jsonb),
    ('lineage_ingest', 'LineageIngest', 'dev-lineage-ingest-hash', TRUE,
     '{"required_facet_keys":["source_system","edge_type","lineage_decision"],"commit_decisions":["CRITICAL"],"default_policy_id":"lineage-critical-us","port":8130}'::jsonb),
    ('content_guard', 'ContentGuard', 'dev-content-guard-hash', TRUE,
     '{"required_facet_keys":["content_decision","principal_id"],"commit_decisions":["ALLOWED","REDACTED"],"default_policy_id":"content-high-us","port":8131}'::jsonb)
ON CONFLICT (platform_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    enabled = EXCLUDED.enabled,
    manifest_json = EXCLUDED.manifest_json;

INSERT INTO crystal_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform, block_commit, enabled)
SELECT v.parent_platform, v.parent_facet_key, v.parent_facet_value, v.child_platform, TRUE, TRUE
FROM (VALUES
    ('content_guard', 'content_decision', 'BLOCKED', 'egress_govern'),
    ('content_guard', 'content_decision', 'BLOCKED', 'incident_response_gate'),
    ('lineage_ingest', 'lineage_decision', 'CRITICAL', 'egress_govern')
) AS v(parent_platform, parent_facet_key, parent_facet_value, child_platform)
WHERE NOT EXISTS (
    SELECT 1 FROM crystal_mesh_rules m
    WHERE m.parent_platform = v.parent_platform
      AND m.parent_facet_key = v.parent_facet_key
      AND m.parent_facet_value = v.parent_facet_value
      AND m.child_platform = v.child_platform
);
