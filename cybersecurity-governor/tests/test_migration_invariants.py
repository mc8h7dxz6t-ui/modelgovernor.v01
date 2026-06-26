"""Migration invariant definitions for Cybersecurity Governor."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
HELM_MIGRATIONS = ROOT.parent / "deploy" / "helm" / "cybersecuritygovernor" / "files" / "migrations"

REQUIRED = [
    "0001_cg_spine_init.sql",
    "0002_security_chain_anchors.sql",
    "0003_admin_audit_log.sql",
    "0004_cg_platforms_mesh.sql",
    "0005_cg_production_state.sql",
]


def test_invariant_migration_files_present() -> None:
    for name in REQUIRED:
        assert (MIGRATIONS / name).is_file(), f"missing migration {name}"


def test_helm_migration_bundle_matches_source() -> None:
    for name in REQUIRED:
        source = (MIGRATIONS / name).read_text()
        bundled = (HELM_MIGRATIONS / name).read_text()
        assert source == bundled, f"helm bundle drift for {name}"


def test_security_events_hash_chain_migration_present() -> None:
    body = (MIGRATIONS / "0001_cg_spine_init.sql").read_text()
    assert "security_events" in body
    assert "row_hash" in body


def test_security_chain_anchors_migration_present() -> None:
    body = (MIGRATIONS / "0002_security_chain_anchors.sql").read_text()
    assert "security_chain_anchors" in body


def test_security_mesh_migration_present() -> None:
    body = (MIGRATIONS / "0004_cg_platforms_mesh.sql").read_text()
    assert "crystal_mesh_rules" in body
    assert "egress_govern" in body
