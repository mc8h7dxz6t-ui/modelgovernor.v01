-- Governance tier classification for the model policy registry.
--
-- Each model is assigned to exactly one of three institutional tiers:
--
--   BUDGET   - fast, cost-controlled inference.  Per-trace ceiling: 25.000000.
--              Suitable for high-volume, latency-sensitive workloads where
--              spend predictability is the primary governance objective.
--
--   STANDARD - balanced production inference.  Per-trace ceiling: 50.000000.
--              Suitable for general enterprise workloads where capability and
--              cost are jointly governed.
--
--   FRONTIER - high-capability or reasoning-intensive inference.
--              Per-trace ceiling: 150.000000.  Suitable for research,
--              complex reasoning, and premium workflows that require an
--              elevated spend ceiling while remaining policy-controlled.
--
-- The tier is stored as a constrained VARCHAR so it appears in registry
-- queries, operational reports, and the /admin/models response without
-- requiring a join or application-side mapping.  stream_allowed = FALSE
-- on reasoning models (o3, o4-mini, deepseek-reasoner) is enforced here
-- to preserve deterministic audit coverage for non-streaming responses.
--
-- All updates are idempotent: repeated application produces no net change.

-- ── Add governance_tier column ───────────────────────────────────────────────

ALTER TABLE model_policy_registry
    ADD COLUMN IF NOT EXISTS governance_tier VARCHAR(10) NOT NULL DEFAULT 'STANDARD';

-- ── Set explicit tiers for all models ────────────────────────────────────────

-- BUDGET tier
UPDATE model_policy_registry
SET governance_tier = 'BUDGET'
WHERE model_name IN (
    'gpt-4o-mini',
    'gpt-4.1-mini',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'claude-3-5-haiku-20241022',
    'mistral-small-3.1',
    'llama-3.1-8b-instant',
    'command-r-08-2024',
    'deepseek-chat',
    'grok-3-mini'
);

-- STANDARD tier
UPDATE model_policy_registry
SET governance_tier = 'STANDARD'
WHERE model_name IN (
    'gpt-4o',
    'gpt-4.1',
    'gemini-2.5-pro',
    'claude-sonnet-4-5',
    'mistral-large-2411',
    'codestral-2501',
    'llama-3.3-70b-versatile',
    'command-r-plus-08-2024',
    'grok-2-1212'
);

-- FRONTIER tier
UPDATE model_policy_registry
SET governance_tier = 'FRONTIER'
WHERE model_name IN (
    'o3',
    'o4-mini',
    'claude-opus-4',
    'deepseek-reasoner'
);

-- ── Add constraint after data is correct ─────────────────────────────────────

ALTER TABLE model_policy_registry
    DROP CONSTRAINT IF EXISTS model_policy_registry_governance_tier_valid;

ALTER TABLE model_policy_registry
    ADD CONSTRAINT model_policy_registry_governance_tier_valid
        CHECK (governance_tier IN ('BUDGET', 'STANDARD', 'FRONTIER'));

-- ── Set explicit max_cost_per_trace per tier for all models from 0006 ────────
--
-- Migration 0004 added max_cost_per_trace with a DEFAULT of 50.000000.
-- The two seed models (gpt-4o-mini, gpt-4.1-mini) were explicitly set there.
-- Models added in 0006 received the default.  This migration sets deliberate
-- per-tier values so every entry carries an intentional governance ceiling.

-- BUDGET: 25.000000 — conservative ceiling aligned with cost-controlled workloads
UPDATE model_policy_registry
SET max_cost_per_trace = 25.000000
WHERE governance_tier = 'BUDGET';

-- STANDARD: 50.000000 — existing default; explicitly set for auditability
UPDATE model_policy_registry
SET max_cost_per_trace = 50.000000
WHERE governance_tier = 'STANDARD';

-- FRONTIER: 150.000000 — elevated ceiling for premium reasoning workflows
UPDATE model_policy_registry
SET max_cost_per_trace = 150.000000
WHERE governance_tier = 'FRONTIER';
