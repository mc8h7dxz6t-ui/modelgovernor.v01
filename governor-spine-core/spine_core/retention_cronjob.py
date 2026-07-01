"""K4 — retention CronJob Helm conformance across all four governors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spine_core.config import GovernorDomain

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RetentionCronjobSpec:
    helm_template_rel: str
    values_key: str


RETENTION_CRONJOB_REGISTRY: dict[GovernorDomain, RetentionCronjobSpec] = {
    GovernorDomain.MODEL: RetentionCronjobSpec(
        helm_template_rel="deploy/helm/modelgovernor/templates/ledger-retention-cronjob.yaml",
        values_key="ledgerRetention",
    ),
    GovernorDomain.FINANCE: RetentionCronjobSpec(
        helm_template_rel="finance-governor/deploy/helm/finance-governor/templates/decision-retention-cronjob.yaml",
        values_key="decisionRetention",
    ),
    GovernorDomain.INSURANCE: RetentionCronjobSpec(
        helm_template_rel="deploy/helm/insurancegovernor/templates/ledger-retention-cronjob.yaml",
        values_key="ledgerRetention",
    ),
    GovernorDomain.CYBER: RetentionCronjobSpec(
        helm_template_rel="deploy/helm/cybersecuritygovernor/templates/ledger-retention-cronjob.yaml",
        values_key="ledgerRetention",
    ),
}


def retention_cronjob_conformance_failures(repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    failures: list[str] = []

    for domain, spec in RETENTION_CRONJOB_REGISTRY.items():
        path = root / spec.helm_template_rel
        if not path.is_file():
            failures.append(f"{domain.value}: missing Helm retention CronJob {spec.helm_template_rel}")
            continue
        source = path.read_text(encoding="utf-8")
        if "kind: CronJob" not in source:
            failures.append(f"{domain.value}: {spec.helm_template_rel} must define a CronJob")
        if "retention" not in source.lower():
            failures.append(f"{domain.value}: {spec.helm_template_rel} must reference retention runner")
        if spec.values_key not in source:
            failures.append(
                f"{domain.value}: {spec.helm_template_rel} must gate on .Values.{spec.values_key}.enabled"
            )

    return failures
