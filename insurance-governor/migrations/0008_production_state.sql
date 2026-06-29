-- Production state storage — replace in-memory platform dicts with durable Postgres

CREATE TABLE IF NOT EXISTS payment_idempotency (
    idempotency_key VARCHAR(512) PRIMARY KEY,
    payment_id VARCHAR(255) NOT NULL,
    claim_id VARCHAR(255) NOT NULL,
    amount NUMERIC(24, 12) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    payee_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    rail VARCHAR(64) NOT NULL DEFAULT 'ach_stub',
    reference TEXT,
    crystal_id VARCHAR(255),
    external_ref VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS payment_idempotency_claim_idx ON payment_idempotency (claim_id);
CREATE INDEX IF NOT EXISTS payment_idempotency_status_idx ON payment_idempotency (status);

CREATE TABLE IF NOT EXISTS claim_commitments (
    claim_id VARCHAR(255) PRIMARY KEY,
    commitment_id VARCHAR(255) NOT NULL,
    commitment_hash CHAR(64) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    fact_count INT NOT NULL,
    private_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
    sealed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS claim_commitments_hash_idx ON claim_commitments (commitment_hash);

CREATE TABLE IF NOT EXISTS oracle_feed_cache (
    feed_key VARCHAR(255) PRIMARY KEY,
    source VARCHAR(128) NOT NULL,
    metric_value NUMERIC(24, 12) NOT NULL,
    threshold NUMERIC(24, 12) NOT NULL,
    payload JSONB NOT NULL,
    attestation_hash CHAR(64) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS oracle_feed_cache_source_idx ON oracle_feed_cache (source, fetched_at DESC);
