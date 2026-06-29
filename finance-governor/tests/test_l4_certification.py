"""L4 certification checklist validation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_l4_enterprise_values_exists():
    assert (ROOT / "deploy/helm/finance-governor/values-enterprise.yaml").is_file()


def test_l4_argocd_application_exists():
    assert (ROOT / "deploy/argocd/application-production.yaml").is_file()


def test_l4_enterprise_kustomize_exists():
    assert (ROOT / "deploy/kustomize/overlays/enterprise/kustomization.yaml").is_file()


def test_l4_certification_doc_exists():
    assert (ROOT / "docs" / "l4-certification.md").is_file() or (
        ROOT.parent / "docs/finance-governor/l4-certification.md"
    ).is_file()


def test_platform_sdk_doc_exists():
    assert (ROOT / "docs/platform-sdk.md").is_file()


def test_plug_and_play_doc_exists():
    assert (ROOT / "docs/plug-and-play.md").is_file()


def test_chaos_test_exists():
    assert (ROOT / "tests/chaos/test_toxiproxy_fg_spine.py").is_file()


def test_fg_ci_workflow_exists():
    assert (ROOT.parent / ".github/workflows/fg-ci.yml").is_file()
