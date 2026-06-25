"""L4 certification checklist validation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def test_l4_enterprise_values_exists():
    assert (REPO / "deploy/helm/insurancegovernor/values-enterprise.yaml").is_file()


def test_l4_rds_overlay_exists():
    assert (REPO / "deploy/helm/insurancegovernor/values-rds.yaml").is_file()


def test_l4_argocd_application_exists():
    assert (REPO / "deploy/argocd/application-insurancegovernor-production-helm.yaml").is_file()


def test_l4_certification_doc_exists():
    assert (REPO / "docs/insurance-governor/l4-certification.md").is_file()


def test_soc2_evidence_pack_exists():
    assert (REPO / "docs/insurance-governor/soc2-evidence-pack.md").is_file()


def test_certification_program_exists():
    assert (ROOT / "certification/program.yaml").is_file()


def test_chaos_test_exists():
    assert (ROOT / "tests/chaos/test_toxiproxy_claim_ops.py").is_file()


def test_operations_runbook_exists():
    assert (REPO / "docs/insurance-governor/operations-runbook.md").is_file()
