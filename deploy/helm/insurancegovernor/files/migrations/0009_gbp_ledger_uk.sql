-- UK GBP reserve ledger rows for motor / London market policies

INSERT INTO reserve_ledgers (account_id, ledger_type, currency, balance, active)
VALUES
    ('carrier-default', 'case', 'GBP', 50000000.000000000000, TRUE),
    ('carrier-uk-lloyd', 'case', 'GBP', 25000000.000000000000, TRUE)
ON CONFLICT (account_id, ledger_type, currency) DO NOTHING;

INSERT INTO coverage_policy_registry (
    policy_id, line_of_business, platform, jurisdiction, risk_classification,
    max_reserve_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('claim-motor-uk-gbp', 'casualty', 'claim_gate', 'UK', 'high', 3500000.000000000000, 300000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;
