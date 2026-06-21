INSERT INTO model_policies (
    tenant_id,
    provider,
    model_name,
    enabled,
    max_input_tokens,
    max_output_tokens,
    max_cost_per_request,
    stream_allowed,
    fallback_price_per_token
) VALUES
    ('default', 'openai', 'gpt-4o-mini', TRUE, 128000, 4096, 5.000000, TRUE, 0.00005000),
    ('default', 'openai', 'gpt-4.1-mini', TRUE, 128000, 4096, 10.000000, TRUE, 0.00008000)
ON CONFLICT (tenant_id, provider, model_name) DO NOTHING;

INSERT INTO wallets (
    tenant_id,
    wallet_ref,
    currency_code,
    balance_available,
    balance_reserved,
    is_active
) VALUES
    ('default', 'demo-user', 'USD', 100.000000, 0, TRUE)
ON CONFLICT (tenant_id, wallet_ref) DO NOTHING;
