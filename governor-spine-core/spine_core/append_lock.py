"""H1 — append-path advisory lock conformance across all four governors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spine_core.config import GovernorDomain

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AppendLockSpec:
    rel_path: str
    append_fn: str


APPEND_LOCK_REGISTRY: dict[GovernorDomain, AppendLockSpec] = {
    GovernorDomain.MODEL: AppendLockSpec(
        rel_path="sidecar/app/ledger_events.py",
        append_fn="append_sealed_ledger_event",
    ),
    GovernorDomain.FINANCE: AppendLockSpec(
        rel_path="finance-governor/spine/sidecar/app/decision_seal.py",
        append_fn="append_decision_event",
    ),
    GovernorDomain.INSURANCE: AppendLockSpec(
        rel_path="insurance-governor/spine/sidecar/app/claim_events.py",
        append_fn="append_claim_event",
    ),
    GovernorDomain.CYBER: AppendLockSpec(
        rel_path="cybersecurity-governor/spine/sidecar/app/security_events.py",
        append_fn="append_security_event",
    ),
}


def append_lock_conformance_failures(repo_root: Path | None = None) -> list[str]:
    """Static H1 checks — append helpers must acquire chain_append_lock."""
    root = repo_root or REPO_ROOT
    failures: list[str] = []

    for domain, spec in APPEND_LOCK_REGISTRY.items():
        path = root / spec.rel_path
        if not path.is_file():
            failures.append(f"{domain.value}: missing append module {spec.rel_path}")
            continue

        source = path.read_text(encoding="utf-8")
        if f"def {spec.append_fn}" not in source:
            failures.append(f"{domain.value}: missing {spec.append_fn}() in {spec.rel_path}")
        if "chain_append_lock" not in source:
            failures.append(
                f"{domain.value}: {spec.rel_path} must wrap {spec.append_fn}() "
                "with spine_core.chain_advisory_lock.chain_append_lock"
            )

    return failures
