-- Demo + gateway multi-provider routing models (sidecar FK on escrow_ledger.model).
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
    ('anthropic/claude-3-5-haiku-latest', 'anthropic', TRUE, 128000, 4096, 5.000000, TRUE, 0.000050),
    ('vertex/gemini-1.5-flash', 'vertex', TRUE, 128000, 4096, 5.000000, TRUE, 0.000050)
ON CONFLICT (model_name) DO NOTHING;
