-- Production state — idempotent security actions + SIEM export cache

CREATE TABLE IF NOT EXISTS security_action_idempotency (
    idempotency_key VARCHAR(512) PRIMARY KEY,
    action_id VARCHAR(255) NOT NULL,
    platform VARCHAR(64) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    reference TEXT,
    crystal_id VARCHAR(255),
    external_ref VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS security_action_idempotency_platform_idx
    ON security_action_idempotency (platform, status);

CREATE TABLE IF NOT EXISTS siem_export_cache (
    export_key VARCHAR(255) PRIMARY KEY,
    framework VARCHAR(64) NOT NULL,
    control_id VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    evidence_hash CHAR(64) NOT NULL,
    exported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS siem_export_cache_framework_idx
    ON siem_export_cache (framework, exported_at DESC);
