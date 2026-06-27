-- Platform persistence — append-only audit + durable state (Phase 3 production)

CREATE TABLE platform_events (
    event_id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    operation_id VARCHAR(255) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_platform_events_platform_time
ON platform_events (platform, recorded_at DESC);

CREATE INDEX idx_platform_events_operation
ON platform_events (platform, operation_id);

-- SubledgerSync
CREATE TABLE subledger_transactions (
    txn_hash VARCHAR(64) PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    counterparty_id VARCHAR(255) NOT NULL,
    amount NUMERIC(24, 12) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    value_date VARCHAR(20) NOT NULL,
    reference TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    fx_hash VARCHAR(64),
    mirror_hash VARCHAR(64),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subledger_pending
ON subledger_transactions (status, recorded_at)
WHERE status = 'PENDING';

-- AssetLedger
CREATE TABLE asset_ledger_assets (
    asset_id VARCHAR(255) PRIMARY KEY,
    description TEXT NOT NULL,
    acquisition_cost NUMERIC(24, 12) NOT NULL,
    book_value NUMERIC(24, 12) NOT NULL,
    accumulated_depreciation NUMERIC(24, 12) NOT NULL DEFAULT 0,
    method VARCHAR(50) NOT NULL DEFAULT 'straight_line',
    jurisdiction VARCHAR(10) NOT NULL DEFAULT 'US',
    useful_life_months INT NOT NULL DEFAULT 60,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fg_asset_book_nonnegative CHECK (book_value >= 0)
);

CREATE TABLE asset_depreciation_charges (
    asset_id VARCHAR(255) NOT NULL REFERENCES asset_ledger_assets(asset_id),
    period VARCHAR(20) NOT NULL,
    charge NUMERIC(24, 12) NOT NULL,
    reg_table_version VARCHAR(50),
    crystal_id VARCHAR(255),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_id, period)
);

-- CreditGovern audit trail
CREATE TABLE credit_evaluations (
    application_id VARCHAR(255) PRIMARY KEY,
    decision VARCHAR(20) NOT NULL,
    exposure_amount NUMERIC(24, 12) NOT NULL,
    model_version_id VARCHAR(100) NOT NULL,
    desk_id VARCHAR(255) NOT NULL,
    score NUMERIC(10, 6),
    explanation_id VARCHAR(255),
    crystal_id VARCHAR(255),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
