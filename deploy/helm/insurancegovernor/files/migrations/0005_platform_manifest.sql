-- Platform manifest column + full plug-and-play registry seed

ALTER TABLE platform_registry ADD COLUMN IF NOT EXISTS manifest_json JSONB NOT NULL DEFAULT '{}'::jsonb;

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled, manifest_json)
VALUES
    (
        'claim_gate',
        'ClaimGate',
        'dev-claim-gate-hash',
        TRUE,
        '{"required_facet_keys":["claim_id"],"commit_decisions":["APPROVED"],"default_policy_id":"claim-high-us","port":8103}'::jsonb
    ),
    (
        'bind_authority',
        'BindAuthority',
        'dev-bind-authority-hash',
        TRUE,
        '{"required_facet_keys":["application_id"],"commit_decisions":["BOUND"],"default_policy_id":"bind-standard-us","port":8104}'::jsonb
    ),
    (
        'parametric_oracle',
        'ParametricOracle',
        'dev-parametric-oracle-hash',
        TRUE,
        '{"required_facet_keys":["event_id","oracle_attestation_hash"],"commit_decisions":["TRIGGERED"],"default_policy_id":"parametric-cat-us","port":8105}'::jsonb
    )
ON CONFLICT (platform_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    enabled = EXCLUDED.enabled,
    manifest_json = EXCLUDED.manifest_json;
