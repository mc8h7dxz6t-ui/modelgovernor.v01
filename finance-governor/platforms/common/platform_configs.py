"""Canonical PlatformConfig definitions for the Finance Governor fleet."""
from __future__ import annotations

from .platform_sdk import PlatformConfig

WIRE_MATCH_CONFIG = PlatformConfig(
    name="wire_match",
    display_name="WireMatch",
    default_risk_tier="critical",
    default_policy_id="wire-critical-us",
    facet_schema={
        "required": ["amount"],
        "properties": {
            "amount": {"type": "string"},
            "currency": {"type": "string"},
            "beneficiary_hash": {"type": "string"},
        },
    },
    invariant_counters=(
        "wire_held_total",
        "wire_approved_total",
        "wire_sent_below_threshold_total",
    ),
)

ALGOFREEZE_CONFIG = PlatformConfig(
    name="algofreeze",
    display_name="AlgoFreeze",
    default_risk_tier="critical",
    default_policy_id="algo-critical-us",
    facet_schema={
        "required": ["runtime_sha"],
        "properties": {
            "runtime_sha": {"type": "string"},
            "freeze_state": {"type": "string"},
        },
    },
    invariant_counters=(
        "frozen_egress_attempt_total",
        "version_mismatch_freeze_total",
        "feed_degraded_total",
    ),
)

SUBLEDGER_CONFIG = PlatformConfig(
    name="subledger_sync",
    display_name="SubledgerSync",
    default_risk_tier="high",
    facet_schema={
        "required": ["entity_id", "amount", "currency"],
        "properties": {
            "entity_id": {"type": "string"},
            "counterparty_id": {"type": "string"},
            "amount": {"type": "string"},
            "currency": {"type": "string"},
        },
    },
    invariant_counters=(
        "ic_matched_total",
        "ic_orphan_detected_total",
        "match_tolerance_breach_total",
        "fx_snapshot_failed_total",
    ),
)

ASSET_LEDGER_CONFIG = PlatformConfig(
    name="asset_ledger",
    display_name="AssetLedger",
    default_risk_tier="high",
    facet_schema={
        "required": ["asset_id"],
        "properties": {
            "asset_id": {"type": "string"},
            "period": {"type": "string"},
        },
    },
    invariant_counters=(
        "negative_book_value_total",
        "depreciation_duplicate_blocked_total",
    ),
)

CREDIT_GOVERN_CONFIG = PlatformConfig(
    name="credit_govern",
    display_name="CreditGovern",
    default_risk_tier="high",
    default_policy_id="credit-high-us",
    facet_schema={
        "required": ["application_id", "exposure_amount", "model_version_id"],
        "properties": {
            "application_id": {"type": "string"},
            "exposure_amount": {"type": "string"},
            "model_version_id": {"type": "string"},
            "desk_id": {"type": "string"},
        },
    },
    invariant_counters=(
        "rail_attempt_total",
        "rail_circuit_open_total",
        "model_version_blocked_total",
        "attribution_identity_mismatch_total",
        "bias_cohort_alert_total",
    ),
)
