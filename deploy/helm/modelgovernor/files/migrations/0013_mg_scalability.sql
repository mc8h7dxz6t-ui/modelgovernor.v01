-- ModelGovernor — institutional++ scalability hardening

CREATE INDEX IF NOT EXISTS idx_mg_ledger_events_tenant
    ON ledger_events (tenant_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_mg_ledger_events_verify
    ON ledger_events (event_id)
    INCLUDE (row_hash, prev_hash);

CREATE INDEX IF NOT EXISTS idx_mg_ledger_events_recorded_brin
    ON ledger_events USING BRIN (recorded_at);

CREATE TABLE IF NOT EXISTS ledger_chain_verify_checkpoints (
    checkpoint_id BIGSERIAL PRIMARY KEY,
    singleton_key SMALLINT NOT NULL DEFAULT 1 UNIQUE,
    last_verified_event_id BIGINT NOT NULL,
    verified_head_hash VARCHAR(64) NOT NULL,
    sealed_count BIGINT NOT NULL,
    total_events BIGINT NOT NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT mg_checkpoint_singleton CHECK (singleton_key = 1)
);

CREATE TABLE IF NOT EXISTS ledger_events_retention_policy (
    policy_id VARCHAR(64) PRIMARY KEY,
    hot_days INT NOT NULL DEFAULT 90,
    warm_days INT NOT NULL DEFAULT 365,
    archive_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ledger_events_retention_policy (policy_id, hot_days, warm_days, archive_enabled)
VALUES ('default', 90, 365, FALSE)
ON CONFLICT (policy_id) DO NOTHING;
