"""L4 certification checklist validation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def test_l4_enterprise_values_exists():
    assert (REPO / "deploy/helm/cybersecuritygovernor/values-enterprise.yaml").is_file()


def test_l4_rds_overlay_exists():
    assert (REPO / "deploy/helm/cybersecuritygovernor/values-rds.yaml").is_file()


def test_l4_argocd_application_exists():
    assert (REPO / "deploy/argocd/application-cybersecuritygovernor-production-helm.yaml").is_file()


def test_l4_certification_doc_exists():
    assert (REPO / "docs/cybersecurity-governor/l4-certification.md").is_file()


def test_soc2_evidence_pack_exists():
    assert (REPO / "docs/cybersecurity-governor/soc2-evidence-pack.md").is_file()


def test_certification_program_exists():
    assert (ROOT / "certification/program.yaml").is_file()


def test_chaos_test_exists():
    assert (ROOT / "tests/chaos/test_toxiproxy_security_ops.py").is_file()


def test_operations_runbook_exists():
    assert (REPO / "docs/cybersecurity-governor/operations-runbook.md").is_file()


def test_l4_security_anchor_bucket_exists():
    assert (REPO / "deploy/infra/aws/security-anchor-bucket.yaml").is_file()
