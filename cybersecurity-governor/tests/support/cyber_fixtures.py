"""Shared Cybersecurity Governor test facets and platform helpers."""
from __future__ import annotations


def egress_facets(
    *,
    flow_id: str = "flow-1",
    host: str = "api.openai.com",
    decision: str = "ALLOWED",
) -> dict[str, str]:
    return {
        "flow_id": flow_id,
        "destination_host": host,
        "egress_decision": decision,
    }


def compliance_facets(
    *,
    framework: str = "SOC2",
    control_id: str = "CC6.1",
    evidence_hash: str = "abc123",
) -> dict[str, str]:
    return {
        "framework": framework,
        "control_id": control_id,
        "evidence_hash": evidence_hash,
    }


EGRESS_PLATFORM = "egress_govern"
EGRESS_POLICY = "egress-critical-us"
COMPLIANCE_PLATFORM = "compliance_logger"
COMPLIANCE_POLICY = "compliance-standard-us"
