"""M1 spine consolidation conformance."""

from pathlib import Path

from spine_core.commit_registry import COMMIT_MODULE_REGISTRY
from spine_core.m1_conformance import m1_conformance_failures
from spine_core.verify_route_registry import VERIFY_ROUTE_REGISTRY


def test_m1_commit_and_verify_registries_cover_ccp_governors():
    assert len(COMMIT_MODULE_REGISTRY) == 3
    assert len(VERIFY_ROUTE_REGISTRY) == 4


def test_m1_conformance_no_failures():
    repo_root = Path(__file__).resolve().parents[2]
    failures = m1_conformance_failures(repo_root)
    assert failures == [], "M1 spine consolidation gaps:\n" + "\n".join(failures)
