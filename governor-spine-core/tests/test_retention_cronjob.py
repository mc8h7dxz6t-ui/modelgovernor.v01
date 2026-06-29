"""K4 — retention CronJob Helm conformance."""

from pathlib import Path

from spine_core.retention_cronjob import RETENTION_CRONJOB_REGISTRY, retention_cronjob_conformance_failures


def test_k4_all_four_governors_registered():
    assert len(RETENTION_CRONJOB_REGISTRY) == 4


def test_k4_retention_cronjob_conformance_no_failures():
    repo_root = Path(__file__).resolve().parents[2]
    failures = retention_cronjob_conformance_failures(repo_root)
    assert failures == [], "K4 retention CronJob gaps:\n" + "\n".join(failures)
