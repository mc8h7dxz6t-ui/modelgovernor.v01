-- Tamper-evident privileged admin action audit trail.

CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    actor_subject TEXT NOT NULL,
    actor_method VARCHAR(32) NOT NULL,
    actor_roles TEXT,
    action VARCHAR(128) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    prev_hash CHAR(64),
    row_hash CHAR(64),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_recorded_at
    ON admin_audit_log (recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_action
    ON admin_audit_log (action, recorded_at DESC);
