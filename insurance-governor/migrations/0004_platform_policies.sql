-- Platform policies for BindAuthority and ParametricOracle

INSERT INTO coverage_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_reserve_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('bind-standard-us', 'commercial', 'bind_authority', 'US', 'high', 2500000.000000000000, 600000, FALSE),
    ('parametric-cat-us', 'property', 'parametric_oracle', 'US', 'critical', 10000000.000000000000, 60000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;

INSERT INTO platform_registry (platform_name, display_name, auth_token_hash, enabled)
VALUES
    ('bind_authority', 'Bind Authority', 'dev-bind-authority-hash', TRUE),
    ('parametric_oracle', 'Parametric Oracle', 'dev-parametric-oracle-hash', TRUE)
ON CONFLICT (platform_name) DO NOTHING;
