-- Platform SDK — registry runtime, facet schemas, plug-and-play fleet

ALTER TABLE platform_registry ADD COLUMN IF NOT EXISTS base_url VARCHAR(512);
ALTER TABLE platform_registry ADD COLUMN IF NOT EXISTS default_policy_id VARCHAR(255);
ALTER TABLE platform_registry ADD COLUMN IF NOT EXISTS default_risk_tier VARCHAR(20) NOT NULL DEFAULT 'high';
ALTER TABLE platform_registry ADD COLUMN IF NOT EXISTS facet_schema JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE platform_registry ADD COLUMN IF NOT EXISTS invariant_counters JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Built-in fleet (idempotent)
INSERT INTO platform_registry (
    platform_name, display_name, auth_token_hash, enabled,
    base_url, default_policy_id, default_risk_tier, facet_schema, invariant_counters
) VALUES
    (
        'wire_match', 'WireMatch', 'builtin', TRUE,
        'http://fg-wirematch:8093', 'wire-critical-us', 'critical',
        '{"required":["amount"],"properties":{"amount":{"type":"string"},"currency":{"type":"string"},"beneficiary_hash":{"type":"string"}}}'::jsonb,
        '["wire_held_total","wire_approved_total","wire_sent_below_threshold_total"]'::jsonb
    ),
    (
        'algofreeze', 'AlgoFreeze', 'builtin', TRUE,
        'http://fg-algofreeze:8094', 'algo-critical-us', 'critical',
        '{"required":["runtime_sha"],"properties":{"runtime_sha":{"type":"string"},"freeze_state":{"type":"string"}}}'::jsonb,
        '["frozen_egress_attempt_total","version_mismatch_freeze_total","feed_degraded_total"]'::jsonb
    ),
    (
        'subledger_sync', 'SubledgerSync', 'builtin', TRUE,
        'http://fg-subledger:8095', NULL, 'high',
        '{"required":["entity_id","amount","currency"],"properties":{"entity_id":{"type":"string"},"counterparty_id":{"type":"string"},"amount":{"type":"string"},"currency":{"type":"string"}}}'::jsonb,
        '["ic_matched_total","ic_orphan_detected_total","match_tolerance_breach_total","fx_snapshot_failed_total"]'::jsonb
    ),
    (
        'asset_ledger', 'AssetLedger', 'builtin', TRUE,
        'http://fg-assetledger:8096', NULL, 'high',
        '{"required":["asset_id"],"properties":{"asset_id":{"type":"string"},"period":{"type":"string"}}}'::jsonb,
        '["negative_book_value_total","depreciation_duplicate_blocked_total"]'::jsonb
    ),
    (
        'credit_govern', 'CreditGovern', 'builtin', TRUE,
        'http://fg-creditgovern:8097', 'credit-high-us', 'high',
        '{"required":["application_id","exposure_amount","model_version_id"],"properties":{"application_id":{"type":"string"},"exposure_amount":{"type":"string"},"model_version_id":{"type":"string"},"desk_id":{"type":"string"}}}'::jsonb,
        '["rail_attempt_total","rail_circuit_open_total","model_version_blocked_total","attribution_identity_mismatch_total"]'::jsonb
    )
ON CONFLICT (platform_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    base_url = EXCLUDED.base_url,
    default_policy_id = EXCLUDED.default_policy_id,
    default_risk_tier = EXCLUDED.default_risk_tier,
    facet_schema = EXCLUDED.facet_schema,
    invariant_counters = EXCLUDED.invariant_counters,
    enabled = EXCLUDED.enabled;
