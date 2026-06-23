-- Phase 4: reporting-oriented admin audit log columns and indexes.

ALTER TABLE admin_audit_log
    ADD COLUMN wallet_id VARCHAR(255);

ALTER TABLE admin_audit_log
    ADD COLUMN operation_id VARCHAR(255);

ALTER TABLE admin_audit_log
    ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE admin_audit_log
    ADD COLUMN event_type VARCHAR(50);

UPDATE admin_audit_log
SET
    created_at = COALESCE(created_at, applied_at),
    event_type = COALESCE(event_type, action_type)
WHERE event_type IS NULL OR created_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_wallet_created
    ON admin_audit_log (wallet_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_operation_event
    ON admin_audit_log (operation_id, event_type);
