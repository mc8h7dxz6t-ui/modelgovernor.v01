"""Tests for governor-spine-core configuration contract."""

from spine_core.config import DOMAIN_PORTS, DOMAIN_REGISTRY, GovernorDomain, MATURITY_LABEL
from spine_core.port_checks import port_alignment_failures


def test_all_four_governors_registered():
    assert len(DOMAIN_PORTS) == 4
    assert len(DOMAIN_REGISTRY) == 4


def test_cyber_ports_are_812x():
    cyber = DOMAIN_PORTS[GovernorDomain.CYBER]
    assert cyber.gateway == 8120
    assert cyber.sidecar == 8121
    assert cyber.reconciler == 8122


def test_maturity_label_is_self_check_not_l5_marketing():
    assert "Self-Check" in MATURITY_LABEL
    assert "Industry Leading" not in MATURITY_LABEL


def test_spine_dockerfile_compose_port_alignment():
    failures = port_alignment_failures()
    assert failures == [], "port misalignment:\n" + "\n".join(failures)
