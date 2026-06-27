-- Cybersecurity Governor platforms + Security Enforcement Mesh

ALTER TABLE platform_registry ADD COLUMN IF NOT EXISTS manifest_json JSONB NOT NULL DEFAULT '{}'::jsonb;

INSERT INTO security_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_budget_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('egress-critical-us', 'network', 'egress_govern', 'US', 'critical', 1000000.000000000000, 15000, FALSE),
    ('identity-high-us', 'iam', 'identity_govern', 'US', 'high', 500000.000000000000, 60000, FALSE),
    ('threat-critical-us', 'detection', 'threat_proxy', 'US', 'critical', 2000000.000000000000, 10000, FALSE),
    ('ir-critical-us', 'response', 'incident_response_gate', 'US', 'critical', 5000000.000000000000, 30000, FALSE),
    ('posture-high-us', 'vuln', 'posture_reconcile', 'US', 'high', 10000000.000000000000, 300000, FALSE),
    ('compliance-standard-us', 'audit', 'compliance_logger', 'US', 'high', 100000.000000000000, 600000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled, manifest_json)
VALUES
    ('egress_govern', 'EgressGovern', 'dev-egress-govern-hash', TRUE,
     '{"required_facet_keys":["flow_id","destination_host","egress_decision"],"commit_decisions":["ALLOWED"],"default_policy_id":"egress-critical-us","port":8123}'::jsonb),
    ('identity_govern', 'IdentityGovern', 'dev-identity-govern-hash', TRUE,
     '{"required_facet_keys":["principal","workload_sa","identity_decision"],"commit_decisions":["VERIFIED"],"default_policy_id":"identity-high-us","port":8124}'::jsonb),
    ('threat_proxy', 'ThreatProxy', 'dev-threat-proxy-hash', TRUE,
     '{"required_facet_keys":["request_id","threat_score","threat_decision"],"commit_decisions":["CLEARED"],"default_policy_id":"threat-critical-us","port":8125}'::jsonb),
    ('incident_response_gate', 'IncidentResponseGate', 'dev-ir-gate-hash', TRUE,
     '{"required_facet_keys":["incident_id","action_type","ir_decision"],"commit_decisions":["AUTHORIZED"],"default_policy_id":"ir-critical-us","port":8126}'::jsonb),
    ('posture_reconcile', 'PostureReconcile', 'dev-posture-reconcile-hash', TRUE,
     '{"required_facet_keys":["asset_id","match_state"],"commit_decisions":["MATCHED"],"default_policy_id":"posture-high-us","port":8127}'::jsonb),
    ('compliance_logger', 'ComplianceLogger', 'dev-compliance-logger-hash', TRUE,
     '{"required_facet_keys":["framework","control_id","evidence_hash"],"commit_decisions":["LOGGED"],"default_policy_id":"compliance-standard-us","port":8128}'::jsonb)
ON CONFLICT (platform_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    enabled = EXCLUDED.enabled,
    manifest_json = EXCLUDED.manifest_json;

-- Security Enforcement Mesh — runtime cross-platform blocks (rivals: GRC post-hoc only)
INSERT INTO crystal_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform, block_commit, enabled)
SELECT v.parent_platform, v.parent_facet_key, v.parent_facet_value, v.child_platform, TRUE, TRUE
FROM (VALUES
    ('posture_reconcile', 'match_state', 'DRIFT', 'egress_govern'),
    ('posture_reconcile', 'match_state', 'DRIFT', 'incident_response_gate'),
    ('threat_proxy', 'threat_decision', 'BLOCKED', 'egress_govern'),
    ('threat_proxy', 'threat_decision', 'BLOCKED', 'incident_response_gate'),
    ('identity_govern', 'identity_decision', 'VIOLATION', 'incident_response_gate'),
    ('identity_govern', 'identity_decision', 'VIOLATION', 'egress_govern'),
    ('egress_govern', 'egress_decision', 'DENIED', 'incident_response_gate')
) AS v(parent_platform, parent_facet_key, parent_facet_value, child_platform)
WHERE NOT EXISTS (
    SELECT 1 FROM crystal_mesh_rules m
    WHERE m.parent_platform = v.parent_platform
      AND m.parent_facet_key = v.parent_facet_key
      AND m.parent_facet_value = v.parent_facet_value
      AND m.child_platform = v.child_platform
);
