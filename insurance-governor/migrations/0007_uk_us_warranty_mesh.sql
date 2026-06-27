-- UK/US jurisdiction policies + warranty enforcement mesh rules (loss-control moat)

INSERT INTO coverage_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_reserve_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('crime-indemnity-us', 'crime', 'indemnity_pay_gate', 'US', 'critical', 5000000.000000000000, 30000, FALSE),
    ('crime-indemnity-uk', 'crime', 'indemnity_pay_gate', 'UK', 'critical', 3000000.000000000000, 30000, FALSE),
    ('model-risk-us', 'cyber', 'model_risk_freeze', 'US', 'critical', 10000000.000000000000, 5000, FALSE),
    ('model-risk-uk', 'cyber', 'model_risk_freeze', 'UK', 'critical', 8000000.000000000000, 5000, FALSE),
    ('underwriting-fair-us', 'commercial', 'underwriting_govern', 'US', 'high', 2500000.000000000000, 600000, FALSE),
    ('underwriting-fair-uk', 'commercial', 'underwriting_govern', 'UK', 'high', 2000000.000000000000, 600000, FALSE),
    ('reserve-sync-us', 'reinsurance', 'reserve_reconcile', 'US', 'high', 10000000.000000000000, 300000, FALSE),
    ('reserve-sync-uk', 'reinsurance', 'reserve_reconcile', 'UK', 'high', 8000000.000000000000, 300000, FALSE),
    ('claim-high-uk', 'casualty', 'claim_gate', 'UK', 'high', 4000000.000000000000, 300000, FALSE),
    ('bind-standard-uk', 'commercial', 'bind_authority', 'UK', 'high', 2000000.000000000000, 600000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled, manifest_json)
VALUES
    (
        'indemnity_pay_gate',
        'IndemnityPayGate',
        'dev-indemnity-pay-gate-hash',
        TRUE,
        '{"required_facet_keys":["payment_id","indemnity_decision"],"commit_decisions":["APPROVED"],"default_policy_id":"crime-indemnity-us","port":8110}'::jsonb
    ),
    (
        'model_risk_freeze',
        'ModelRiskFreeze',
        'dev-model-risk-freeze-hash',
        TRUE,
        '{"required_facet_keys":["inference_id","freeze_state"],"commit_decisions":["ACTIVE"],"default_policy_id":"model-risk-us","port":8111}'::jsonb
    ),
    (
        'underwriting_govern',
        'UnderwritingGovern',
        'dev-underwriting-govern-hash',
        TRUE,
        '{"required_facet_keys":["application_id","govern_decision"],"commit_decisions":["COMPLIANT"],"default_policy_id":"underwriting-fair-us","port":8112}'::jsonb
    ),
    (
        'reserve_reconcile',
        'ReserveReconcile',
        'dev-reserve-reconcile-hash',
        TRUE,
        '{"required_facet_keys":["claim_id","match_state"],"commit_decisions":["MATCHED"],"default_policy_id":"reserve-sync-us","port":8113}'::jsonb
    )
ON CONFLICT (platform_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    enabled = EXCLUDED.enabled,
    manifest_json = EXCLUDED.manifest_json;

-- Warranty Enforcement Engine — cross-platform mesh invariants
INSERT INTO crystal_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform, block_commit, enabled)
SELECT v.parent_platform, v.parent_facet_key, v.parent_facet_value, v.child_platform, TRUE, TRUE
FROM (VALUES
    ('model_risk_freeze', 'freeze_state', 'FROZEN', 'claim_gate'),
    ('model_risk_freeze', 'freeze_state', 'FROZEN', 'indemnity_pay_gate'),
    ('claim_gate', 'gate_decision', 'REFERRED', 'indemnity_pay_gate'),
    ('underwriting_govern', 'govern_decision', 'VIOLATION', 'bind_authority'),
    ('reserve_reconcile', 'match_state', 'DRIFT', 'claim_gate'),
    ('reserve_reconcile', 'match_state', 'DRIFT', 'indemnity_pay_gate')
) AS v(parent_platform, parent_facet_key, parent_facet_value, child_platform)
WHERE NOT EXISTS (
    SELECT 1 FROM crystal_mesh_rules m
    WHERE m.parent_platform = v.parent_platform
      AND m.parent_facet_key = v.parent_facet_key
      AND m.parent_facet_value = v.parent_facet_value
      AND m.child_platform = v.child_platform
);
