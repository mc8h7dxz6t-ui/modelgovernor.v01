-- Witness quorum: immutable anchor of verified security_events chain heads.

CREATE TABLE IF NOT EXISTS security_chain_anchors (
    anchor_id BIGSERIAL PRIMARY KEY,
    head_hash CHAR(64) NOT NULL,
    sealed_count BIGINT NOT NULL,
    total_events BIGINT NOT NULL,
    first_event_id BIGINT,
    last_event_id BIGINT,
    source VARCHAR(64) NOT NULL DEFAULT 'cronjob',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_chain_anchors_recorded_at
    ON security_chain_anchors (recorded_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS security_chain_anchors_one_per_head
    ON security_chain_anchors (head_hash);

-- Structural DAG tier: kernel/runtime lineage edges (Falco, Tetragon, generic).

CREATE TABLE IF NOT EXISTS lineage_edges (
    edge_id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL,
    edge_type VARCHAR(50) NOT NULL,
    parent_ref VARCHAR(512),
    child_ref VARCHAR(512) NOT NULL,
    principal_id VARCHAR(255),
    physical_time TIMESTAMPTZ NOT NULL,
    logical_counter BIGINT NOT NULL DEFAULT 0,
    causal_parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity VARCHAR(20) NOT NULL DEFAULT 'standard',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lineage_edges_parent ON lineage_edges (parent_ref);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_child ON lineage_edges (child_ref);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_principal ON lineage_edges (principal_id, physical_time DESC);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_type ON lineage_edges (edge_type, physical_time DESC);

INSERT INTO control_policy_registry (
    policy_id, instrument_type, platform, jurisdiction, risk_classification,
    max_exposure_per_commit, commit_horizon_ms, allow_auto_expire
) VALUES
    ('lineage-critical-us', 'lineage', 'lineage_ingest', 'US', 'critical', 1000000.000000000000, 30000, FALSE)
ON CONFLICT (policy_id) DO NOTHING;
