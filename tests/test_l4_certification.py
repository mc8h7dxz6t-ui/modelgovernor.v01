"""Tests for L4 Gold Enterprise certification gate (ModelGovernor root)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_l4_helm_production_values_exists():
    assert (ROOT / "deploy/helm/modelgovernor/values-production.yaml").is_file()


def test_l4_helm_staging_values_exists():
    assert (ROOT / "deploy/helm/modelgovernor/values-staging.yaml").is_file()


def test_l4_argocd_application_exists():
    assert (ROOT / "deploy/argocd/application-production.yaml").is_file()


def test_l4_certification_program_exists():
    assert (ROOT / "certification/program.yaml").is_file()


def test_l4_institutional_reliability_doc_exists():
    assert (ROOT / "docs/institutional-reliability.md").is_file()


def test_l4_chaos_compose_exists():
    assert (ROOT / "docker-compose.chaos.yml").is_file()


def test_l4_ci_workflow_exists():
    assert (ROOT / ".github/workflows/ci.yml").is_file()
