-- Finance Governor Phase 1 schema (credit decision wedge)
-- Design artifact — not yet wired to migration runner

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE account_ledgers (
    account_id VARCHAR(255) NOT NULL,
    ledger_type VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    balance NUMERIC(24, 12) NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    lock_reason VARCHAR(255),
    locked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, ledger_type, currency),
    CONSTRAINT account_nonnegative_balance CHECK (balance >= 0)
);

CREATE TABLE instrument_policy_registry (
    policy_id VARCHAR(255) PRIMARY KEY,
    instrument_type VARCHAR(50) NOT NULL,
    model_version_id VARCHAR(255) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    risk_classification VARCHAR(20) NOT NULL,
    max_exposure_per_decision NUMERIC(24, 12) NOT NULL,
    max_auto_approve_amount NUMERIC(24, 12) NOT NULL,
    explainability_required BOOLEAN NOT NULL DEFAULT TRUE,
    allow_auto_expire BOOLEAN NOT NULL DEFAULT FALSE,
    inference_rail_primary VARCHAR(255) NOT NULL,
    inference_rail_fallback VARCHAR(255),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_to TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TYPE decision_status AS ENUM (
    'RESERVED',
    'IN_FLIGHT',
    'PROVIDER_TIMEOUT',
    'SETTLED',
    'EXPIRED',
    'STRANDED',
    'ADJUDICATED'
);

CREATE TABLE decision_escrow_ledger (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    account_id VARCHAR(255) NOT NULL,
    application_id VARCHAR(255) NOT NULL,
    instrument_type VARCHAR(50) NOT NULL,
    policy_id VARCHAR(255) NOT NULL REFERENCES instrument_policy_registry(policy_id),
    tenant_id VARCHAR(255) NOT NULL,
    desk_id VARCHAR(255),
    book_id VARCHAR(255),
    request_fingerprint VARCHAR(64) NOT NULL,
    reserved_exposure NUMERIC(24, 12) NOT NULL,
    approved_amount NUMERIC(24, 12) NOT NULL DEFAULT 0,
    decision_outcome VARCHAR(50),
    status decision_status NOT NULL DEFAULT 'RESERVED',
    explanation_artifact_id VARCHAR(255),
    feature_snapshot_hash VARCHAR(64),
    rail_request_id VARCHAR(255),
    terminal_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    settled_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT decision_nonnegative_reserved CHECK (reserved_exposure >= 0),
    CONSTRAINT decision_nonnegative_approved CHECK (approved_amount >= 0)
);

CREATE TABLE decision_events (
    event_id BIGSERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    exposure_delta NUMERIC(24, 12) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash VARCHAR(64),
    row_hash VARCHAR(64),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_decision_events_audit_trail
ON decision_events (idempotency_key, recorded_at);

CREATE INDEX idx_decision_reconciliation_sweep
ON decision_escrow_ledger (status, expires_at)
INCLUDE (idempotency_key, account_id, reserved_exposure)
WHERE status = 'RESERVED';

CREATE TABLE exposure_budget_state (
    scope_key VARCHAR(512) PRIMARY KEY,
    cap_amount NUMERIC(24, 12) NOT NULL,
    reserved_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    settled_total NUMERIC(24, 12) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT exposure_cap_nonnegative CHECK (cap_amount >= 0),
    CONSTRAINT exposure_reserved_within_cap CHECK (reserved_total <= cap_amount)
);

CREATE TABLE inference_rail_attempts (
    dispatch_attempt_key VARCHAR(255) PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL REFERENCES decision_escrow_ledger(idempotency_key),
    rail_type VARCHAR(50) NOT NULL,
    rail_request_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE model_ownership (
    model_version_id VARCHAR(255) PRIMARY KEY,
    owner_id VARCHAR(255) NOT NULL,
    validator_id VARCHAR(255),
    approver_id VARCHAR(255),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guardrail_incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255),
    incident_type VARCHAR(50) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE decision_lineage (
    idempotency_key VARCHAR(255) PRIMARY KEY REFERENCES decision_escrow_ledger(idempotency_key),
    feature_snapshot_hash VARCHAR(64) NOT NULL,
    model_input_hash VARCHAR(64),
    policy_version VARCHAR(64) NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Seed: consumer credit policy (US, high-risk per EU AI Act mapping for credit scoring)
INSERT INTO instrument_policy_registry (
    policy_id, instrument_type, model_version_id, jurisdiction,
    risk_classification, max_exposure_per_decision, max_auto_approve_amount,
    explainability_required, allow_auto_expire,
    inference_rail_primary, inference_rail_fallback
) VALUES (
    'credit-consumer-v3-us',
    'credit',
    'credit-model-v3.2.1',
    'US',
    'high',
    250000.000000000000,
    50000.000000000000,
    TRUE,
    FALSE,
    'mock-credit-rail',
    'rules-fallback-v1'
);

INSERT INTO account_ledgers (account_id, ledger_type, currency, balance)
VALUES ('desk-consumer-01', 'exposure', 'USD', 10000000.000000000000);

INSERT INTO exposure_budget_state (scope_key, cap_amount)
VALUES ('tenant:acme:desk:consumer-01:day:2026-06-25', 5000000.000000000000);
