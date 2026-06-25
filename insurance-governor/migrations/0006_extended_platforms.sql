-- Extended platform policies + registry for headline wedges and deep ClaimGate

INSERT INTO coverage_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_reserve_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('zk-audit-us', 'casualty', 'zk_claim_audit', 'US', 'critical', 1000000.000000000000, 300000, FALSE),
    ('spatial-property-us', 'property', 'spatial_twin', 'US', 'high', 5000000.000000000000, 300000, FALSE),
    ('ev-battery-us', 'auto', 'battery_liability', 'US', 'critical', 2500000.000000000000, 300000, FALSE),
    ('subrogation-us', 'casualty', 'subrogation_graph', 'US', 'high', 3000000.000000000000, 600000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled, manifest_json)
VALUES
    (
        'zk_claim_audit',
        'ZkClaimAudit',
        'dev-zk-claim-audit-hash',
        TRUE,
        '{"required_facet_keys":["claim_id","commitment_hash"],"commit_decisions":["SEALED","VERIFIED"],"default_policy_id":"zk-audit-us","port":8106}'::jsonb
    ),
    (
        'spatial_twin',
        'SpatialTwin',
        'dev-spatial-twin-hash',
        TRUE,
        '{"required_facet_keys":["claim_id","point_cloud_hash"],"commit_decisions":["APPROVED"],"default_policy_id":"spatial-property-us","port":8107}'::jsonb
    ),
    (
        'battery_liability',
        'BatteryLiability',
        'dev-battery-liability-hash',
        TRUE,
        '{"required_facet_keys":["claim_id"],"commit_decisions":["APPROVED"],"default_policy_id":"ev-battery-us","port":8108}'::jsonb
    ),
    (
        'subrogation_graph',
        'SubrogationGraph',
        'dev-subrogation-graph-hash',
        TRUE,
        '{"required_facet_keys":["claim_id"],"commit_decisions":["RECOVERY_APPROVED"],"default_policy_id":"subrogation-us","port":8109}'::jsonb
    )
ON CONFLICT (platform_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    enabled = EXCLUDED.enabled,
    manifest_json = EXCLUDED.manifest_json;
