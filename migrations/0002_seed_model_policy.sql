INSERT INTO model_policy_registry (
    model_name,
    provider,
    enabled,
    max_input_tokens,
    max_output_tokens,
    max_cost_per_request,
    stream_allowed,
    fallback_price_per_token
) VALUES
    ('gpt-4o-mini', 'openai', TRUE, 128000, 4096, 5.000000, TRUE, 0.000050),
    ('gpt-4.1-mini', 'openai', TRUE, 128000, 4096, 10.000000, TRUE, 0.000080)
ON CONFLICT (model_name) DO NOTHING;

INSERT INTO user_wallets (user_id, balance, active)
VALUES ('demo-user', 100.000000, TRUE)
ON CONFLICT (user_id) DO NOTHING;
