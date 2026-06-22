-- Phase 3 enterprise expansion: provider reconciliation capture and
-- deterministic admin adjustment workflows.

CREATE UNIQUE INDEX IF NOT EXISTS idx_escrow_provider_request_id_not_null
ON escrow_ledger (provider_request_id)
WHERE provider_request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS provider_reconciliations (
    reconciliation_key VARCHAR(255) PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL REFERENCES escrow_ledger(idempotency_key),
    provider VARCHAR(100) NOT NULL,
    provider_request_id VARCHAR(255),
    provider_actual_amount NUMERIC(18, 6) NOT NULL,
    ledger_actual_amount NUMERIC(18, 6) NOT NULL,
    discrepancy_amount NUMERIC(18, 6) NOT NULL,
    status VARCHAR(20) NOT NULL,
    external_reference VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT provider_reconciliations_status_valid
        CHECK (status IN ('MATCHED', 'MISMATCHED', 'RESOLVED')),
    CONSTRAINT provider_reconciliations_nonnegative_provider_actual
        CHECK (provider_actual_amount >= 0),
    CONSTRAINT provider_reconciliations_nonnegative_ledger_actual
        CHECK (ledger_actual_amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_provider_reconciliations_status_created
ON provider_reconciliations (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_provider_reconciliations_idempotency_key
ON provider_reconciliations (idempotency_key, created_at DESC);

CREATE TABLE IF NOT EXISTS provider_adjustments (
    adjustment_key VARCHAR(255) PRIMARY KEY,
    reconciliation_key VARCHAR(255) NOT NULL REFERENCES provider_reconciliations(reconciliation_key),
    idempotency_key VARCHAR(255) NOT NULL REFERENCES escrow_ledger(idempotency_key),
    prior_actual_amount NUMERIC(18, 6) NOT NULL,
    corrected_actual_amount NUMERIC(18, 6) NOT NULL,
    wallet_delta NUMERIC(18, 6) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT provider_adjustments_nonnegative_prior_actual
        CHECK (prior_actual_amount >= 0),
    CONSTRAINT provider_adjustments_nonnegative_corrected_actual
        CHECK (corrected_actual_amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_provider_adjustments_reconciliation_key
ON provider_adjustments (reconciliation_key, created_at DESC);
