-- Finance Governor — institutional++ scalability hardening

ALTER TABLE decision_events
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) NOT NULL DEFAULT 'tenant-default';

ALTER TABLE account_ledgers
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) NOT NULL DEFAULT 'tenant-default';

ALTER TABLE commit_escrow_ledger
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) NOT NULL DEFAULT 'tenant-default';

CREATE INDEX IF NOT EXISTS idx_fg_decision_events_tenant
    ON decision_events (tenant_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_fg_decision_events_verify
    ON decision_events (event_id)
    INCLUDE (row_hash, prev_hash);

CREATE INDEX IF NOT EXISTS idx_fg_decision_events_recorded_brin
    ON decision_events USING BRIN (recorded_at);

CREATE TABLE IF NOT EXISTS decision_chain_verify_checkpoints (
    checkpoint_id BIGSERIAL PRIMARY KEY,
    singleton_key SMALLINT NOT NULL DEFAULT 1 UNIQUE,
    last_verified_event_id BIGINT NOT NULL,
    verified_head_hash VARCHAR(64) NOT NULL,
    sealed_count BIGINT NOT NULL,
    total_events BIGINT NOT NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fg_checkpoint_singleton CHECK (singleton_key = 1)
);

CREATE TABLE IF NOT EXISTS decision_events_retention_policy (
    policy_id VARCHAR(64) PRIMARY KEY,
    hot_days INT NOT NULL DEFAULT 90,
    warm_days INT NOT NULL DEFAULT 365,
    archive_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO decision_events_retention_policy (policy_id, hot_days, warm_days, archive_enabled)
VALUES ('default', 90, 365, FALSE)
ON CONFLICT (policy_id) DO NOTHING;
