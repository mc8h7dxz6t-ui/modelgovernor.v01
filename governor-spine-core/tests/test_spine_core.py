"""Tests for governor-spine-core configuration contract."""

import os

from spine_core.config import DOMAIN_PORTS, DOMAIN_REGISTRY, GovernorDomain, MATURITY_LABEL
from spine_core.mode_contract import (
    RuntimeExecutionMode,
    SpineAttachmentMode,
    failover_env_contract,
    resolve_provider_mode,
    resolve_spine_attachment,
)
from spine_core.port_checks import port_alignment_failures


def test_all_four_governors_registered():
    assert len(DOMAIN_PORTS) == 4
    assert len(DOMAIN_REGISTRY) == 4


def test_cyber_ports_are_812x():
    cyber = DOMAIN_PORTS[GovernorDomain.CYBER]
    assert cyber.gateway == 8120
    assert cyber.sidecar == 8121
    assert cyber.reconciler == 8122


def test_maturity_label_is_l5_self_check_not_industry_leading_marketing():
    assert MATURITY_LABEL == "L5 Institutional Self-Check Certified"
    assert "Industry Leading" not in MATURITY_LABEL


def test_ledger_contract_documents_domain_tables():
    from spine_core.ledger_contract import LEDGER_TABLE_BY_DOMAIN

    assert len(LEDGER_TABLE_BY_DOMAIN) == 4
    assert LEDGER_TABLE_BY_DOMAIN["CYBER_GOVERNOR"] == "security_events"


def test_spine_dockerfile_compose_port_alignment():
    failures = port_alignment_failures()
    assert failures == [], "port misalignment:\n" + "\n".join(failures)


def test_provider_mode_defaults_mock():
    os.environ.pop("PROVIDER_MODE", None)
    assert resolve_provider_mode() == RuntimeExecutionMode.MOCK


def test_cg_spine_attachment_standalone_when_disabled(monkeypatch):
    monkeypatch.setenv("CG_SPINE_ENABLED", "false")
    assert resolve_spine_attachment(GovernorDomain.CYBER) == SpineAttachmentMode.STANDALONE


def test_failover_contract_documents_existing_env_vars():
    contract = failover_env_contract()
    assert "GUARDRAILS_ENABLED" in contract
    assert "CIRCUIT_BREAKER_ENABLED" in contract
