-- Phase 5: orchestration-plane immutable audit log and semantic cache.

CREATE TABLE IF NOT EXISTS orchestration_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    runtime_mode VARCHAR(32) NOT NULL,
    state VARCHAR(32) NOT NULL,
    agent VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orchestration_audit_run
    ON orchestration_audit_log (run_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_orchestration_audit_workflow
    ON orchestration_audit_log (workflow_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS orchestration_semantic_cache (
    cache_key VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    response_json TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orchestration_semantic_cache_expiry
    ON orchestration_semantic_cache (expires_at);
