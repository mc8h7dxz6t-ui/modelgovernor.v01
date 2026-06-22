-- Expand model policy registry to cover all industry-leading AI providers.
--
-- Each model entry specifies:
--   max_input_tokens   -- governance cap on prompt length
--   max_output_tokens  -- governance cap on completion length
--   max_cost_per_request -- hard ceiling per governed request
--   stream_allowed     -- whether streaming is permitted under policy
--   fallback_price_per_token -- conservative estimate used when provider
--                              does not return token usage in the response
--
-- Tiers:
--   Budget   max_cost_per_request  5.000000  fallback ≤ 0.000150
--   Standard max_cost_per_request 20.000000  fallback ≤ 0.000500
--   Frontier max_cost_per_request 75.000000  fallback ≤ 0.002500
--
-- All values use NUMERIC(18,6) exact-decimal arithmetic.
-- All inserts are idempotent via ON CONFLICT DO NOTHING.

-- ── OpenAI ───────────────────────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- Flagship multimodal
    ('gpt-4o',           'openai', TRUE, 128000, 4096, 20.000000, TRUE, 0.000500),
    -- Latest generation
    ('gpt-4.1',          'openai', TRUE, 128000, 4096, 20.000000, TRUE, 0.000400),
    -- Reasoning — higher spend ceiling, streaming restricted
    ('o3',               'openai', TRUE,  32000, 4096, 75.000000, FALSE, 0.002000),
    ('o4-mini',          'openai', TRUE,  64000, 4096, 30.000000, FALSE, 0.000700)
ON CONFLICT (model_name) DO NOTHING;

-- ── Anthropic ────────────────────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- Frontier
    ('claude-opus-4',                 'anthropic', TRUE, 200000, 4096, 75.000000, TRUE, 0.001800),
    -- Balanced production
    ('claude-sonnet-4-5',             'anthropic', TRUE, 200000, 4096, 20.000000, TRUE, 0.000350),
    -- Fast / budget
    ('claude-3-5-haiku-20241022',     'anthropic', TRUE, 200000, 4096,  5.000000, TRUE, 0.000080)
ON CONFLICT (model_name) DO NOTHING;

-- ── Google ───────────────────────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- Frontier — governed context cap below model maximum for institutional control
    ('gemini-2.5-pro',   'google', TRUE, 128000, 8192, 20.000000, TRUE, 0.000450),
    -- Fast / balanced
    ('gemini-2.5-flash', 'google', TRUE, 128000, 8192,  5.000000, TRUE, 0.000075),
    -- Stable baseline
    ('gemini-2.0-flash', 'google', TRUE, 128000, 4096,  5.000000, TRUE, 0.000060)
ON CONFLICT (model_name) DO NOTHING;

-- ── Meta (hosted via Groq) ───────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- Frontier open-weight
    ('llama-3.3-70b-versatile', 'groq', TRUE, 128000, 4096,  5.000000, TRUE, 0.000090),
    -- Fast / efficient open-weight
    ('llama-3.1-8b-instant',    'groq', TRUE, 128000, 4096,  5.000000, TRUE, 0.000025)
ON CONFLICT (model_name) DO NOTHING;

-- ── Mistral AI ───────────────────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- Frontier
    ('mistral-large-2411', 'mistral', TRUE, 128000, 4096, 20.000000, TRUE, 0.000380),
    -- Balanced
    ('mistral-small-3.1',  'mistral', TRUE, 128000, 4096,  5.000000, TRUE, 0.000090),
    -- Coding specialist
    ('codestral-2501',     'mistral', TRUE, 256000, 4096, 10.000000, TRUE, 0.000200)
ON CONFLICT (model_name) DO NOTHING;

-- ── Cohere ───────────────────────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- Enterprise RAG / retrieval
    ('command-r-plus-08-2024', 'cohere', TRUE, 128000, 4096, 20.000000, TRUE, 0.000300),
    -- Efficient retrieval
    ('command-r-08-2024',      'cohere', TRUE, 128000, 4096,  5.000000, TRUE, 0.000150)
ON CONFLICT (model_name) DO NOTHING;

-- ── DeepSeek ─────────────────────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- General (V3)
    ('deepseek-chat',     'deepseek', TRUE, 128000, 4096,  5.000000, TRUE, 0.000070),
    -- Reasoning (R1) — streaming restricted for deterministic audit
    ('deepseek-reasoner', 'deepseek', TRUE,  64000, 4096, 30.000000, FALSE, 0.000550)
ON CONFLICT (model_name) DO NOTHING;

-- ── xAI ──────────────────────────────────────────────────────────────────────

INSERT INTO model_policy_registry (
    model_name, provider, enabled,
    max_input_tokens, max_output_tokens, max_cost_per_request,
    stream_allowed, fallback_price_per_token
) VALUES
    -- Balanced
    ('grok-2-1212', 'xai', TRUE, 128000, 4096, 20.000000, TRUE, 0.000200),
    -- Fast
    ('grok-3-mini',  'xai', TRUE, 128000, 4096,  5.000000, TRUE, 0.000090)
ON CONFLICT (model_name) DO NOTHING;
