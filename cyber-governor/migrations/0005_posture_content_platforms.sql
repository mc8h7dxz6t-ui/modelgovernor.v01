-- PostureReconcile + ContentGuard mesh rules and control policies

INSERT INTO threat_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform)
SELECT 'posture_reconcile', 'posture_state', 'STRANDED', 'egress_lock'
WHERE NOT EXISTS (
    SELECT 1 FROM threat_mesh_rules
    WHERE parent_platform = 'posture_reconcile'
      AND parent_facet_key = 'posture_state'
      AND parent_facet_value = 'STRANDED'
      AND child_platform = 'egress_lock'
);

INSERT INTO threat_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform)
SELECT 'posture_reconcile', 'posture_state', 'STRANDED', 'content_guard'
WHERE NOT EXISTS (
    SELECT 1 FROM threat_mesh_rules
    WHERE parent_platform = 'posture_reconcile'
      AND parent_facet_key = 'posture_state'
      AND parent_facet_value = 'STRANDED'
      AND child_platform = 'content_guard'
);

INSERT INTO threat_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform)
SELECT 'content_guard', 'content_decision', 'BLOCKED', 'egress_lock'
WHERE NOT EXISTS (
    SELECT 1 FROM threat_mesh_rules
    WHERE parent_platform = 'content_guard'
      AND parent_facet_key = 'content_decision'
      AND parent_facet_value = 'BLOCKED'
      AND child_platform = 'egress_lock'
);

INSERT INTO control_policy_registry (
    policy_id, instrument_type, platform, jurisdiction, risk_classification,
    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('posture-high-us', 'posture', 'posture_reconcile', 'US', 'high', 1000000.000000000000, 120000, FALSE),
    ('content-high-us', 'content', 'content_guard', 'US', 'high', 1000000.000000000000, 120000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;
