-- Phase 3: Admin audit log and reconciliation support indexes
--
-- This migration introduces the admin_audit_log table to track all
-- administrative interventions against governance state.  Admin actions
-- (manual operation correction, wallet unlock, etc.) are append-only events
-- that do not reference escrow_ledger directly so that wallet-level actions
-- can also be recorded without FK constraints.
--
-- Optimized indexes for STRANDED operation queries and locked wallet queries
-- are added to support efficient reconciliation dashboard queries.

CREATE TABLE IF NOT EXISTS admin_audit_log (
    log_id        BIGSERIAL   PRIMARY KEY,
    admin_user_id VARCHAR(255)  NOT NULL,
    action_type   VARCHAR(50)   NOT NULL,
    subject_key   VARCHAR(255)  NOT NULL,
    details       JSONB         NOT NULL DEFAULT '{}'::jsonb,
    applied_at    TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE admin_audit_log IS
    'Append-only record of all administrative interventions.  Never modified after insert.';

COMMENT ON COLUMN admin_audit_log.action_type IS
    'One of: OPERATION_CORRECTION, WALLET_UNLOCK.';

COMMENT ON COLUMN admin_audit_log.subject_key IS
    'idempotency_key for operation corrections; user_id for wallet actions.';

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_subject_key
    ON admin_audit_log (subject_key, applied_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_applied_at
    ON admin_audit_log (applied_at DESC);

-- Optimised covering index for STRANDED operation reconciliation scans.
CREATE INDEX IF NOT EXISTS idx_escrow_stranded_reconcile
    ON escrow_ledger (status, created_at DESC)
    WHERE status = 'STRANDED';

-- Index to support efficient locked-wallet dashboard queries.
CREATE INDEX IF NOT EXISTS idx_user_wallets_locked
    ON user_wallets (locked_at DESC)
    WHERE active = FALSE AND locked_at IS NOT NULL;
