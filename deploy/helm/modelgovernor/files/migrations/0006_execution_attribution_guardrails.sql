ALTER TABLE escrow_ledger
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) NOT NULL DEFAULT 'default-tenant',
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255) NOT NULL DEFAULT 'default-session',
ADD COLUMN IF NOT EXISTS agent_run_id VARCHAR(255) NOT NULL DEFAULT 'default-agent-run',
ADD COLUMN IF NOT EXISTS workflow_step VARCHAR(255) NOT NULL DEFAULT 'default-workflow-step',
ADD COLUMN IF NOT EXISTS policy_version VARCHAR(64) NOT NULL DEFAULT 'v1',
ADD COLUMN IF NOT EXISTS input_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS output_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS cached_input_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS cached_output_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS latency_ms BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS retry_count INT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS failover_count INT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS prompt_template_version VARCHAR(255),
ADD COLUMN IF NOT EXISTS system_context_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS tool_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS raw_tool_output TEXT;

ALTER TABLE provider_dispatch_attempts
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) NOT NULL DEFAULT 'default-tenant',
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255) NOT NULL DEFAULT 'default-session',
ADD COLUMN IF NOT EXISTS agent_run_id VARCHAR(255) NOT NULL DEFAULT 'default-agent-run',
ADD COLUMN IF NOT EXISTS workflow_step VARCHAR(255) NOT NULL DEFAULT 'default-workflow-step',
ADD COLUMN IF NOT EXISTS input_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS output_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS cached_input_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS cached_output_tokens BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS latency_ms BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS retry_count INT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS failover_count INT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS prompt_template_version VARCHAR(255),
ADD COLUMN IF NOT EXISTS system_context_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS tool_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS raw_tool_output TEXT;

CREATE TABLE IF NOT EXISTS budget_scope_state (
    scope_type VARCHAR(32) NOT NULL,
    scope_key VARCHAR(255) NOT NULL,
    cap_amount NUMERIC(18, 6) NOT NULL,
    consumed_amount NUMERIC(18, 6) NOT NULL DEFAULT 0.000000,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope_type, scope_key),
    CONSTRAINT budget_scope_nonnegative_cap CHECK (cap_amount >= 0),
    CONSTRAINT budget_scope_nonnegative_consumed CHECK (consumed_amount >= 0)
);

CREATE TABLE IF NOT EXISTS guardrail_incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255),
    user_id VARCHAR(255),
    tenant_id VARCHAR(255),
    session_id VARCHAR(255),
    agent_run_id VARCHAR(255),
    workflow_step VARCHAR(255),
    incident_type VARCHAR(64) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_loop_state (
    scope_key VARCHAR(255) PRIMARY KEY,
    last_signature VARCHAR(255) NOT NULL,
    consecutive_count INT NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_lineage (
    lineage_id BIGSERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    agent_run_id VARCHAR(255) NOT NULL,
    workflow_step VARCHAR(255) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    prompt_template_version VARCHAR(255),
    system_context_hash VARCHAR(255),
    tool_name VARCHAR(255),
    tool_input TEXT,
    raw_tool_output TEXT,
    provider_request_id VARCHAR(255),
    state_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_escrow_ledger_identity
ON escrow_ledger (tenant_id, user_id, session_id, agent_run_id, workflow_step, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_guardrail_incidents_lookup
ON guardrail_incidents (tenant_id, session_id, agent_run_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_execution_lineage_lookup
ON execution_lineage (idempotency_key, recorded_at DESC);
