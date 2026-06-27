-- Finance Governor hardening — admin audit + decision chain anchors

CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    actor_subject VARCHAR(255) NOT NULL,
    actor_method VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash VARCHAR(64),
    row_hash VARCHAR(64),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decision_chain_anchors (
    anchor_id BIGSERIAL PRIMARY KEY,
    head_hash VARCHAR(64) NOT NULL UNIQUE,
    sealed_count INT NOT NULL,
    total_events INT NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'api',
    anchored_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_decision_chain_anchors_head ON decision_chain_anchors (head_hash);
