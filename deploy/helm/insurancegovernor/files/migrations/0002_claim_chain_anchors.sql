-- Immutable time-series anchor of verified claim chain heads.

CREATE TABLE IF NOT EXISTS claim_chain_anchors (
    anchor_id BIGSERIAL PRIMARY KEY,
    head_hash CHAR(64) NOT NULL,
    sealed_count BIGINT NOT NULL,
    total_events BIGINT NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'cronjob',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claim_chain_anchors_recorded_at
    ON claim_chain_anchors (recorded_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS claim_chain_anchors_one_per_head
    ON claim_chain_anchors (head_hash);
