"""M1 commit module registry — CCP crystallize/commit paths per governor."""

from __future__ import annotations

from dataclasses import dataclass

from spine_core.config import GovernorDomain

REPO_ROOT_MARKER = "commit_ledger.py"


@dataclass(frozen=True)
class CommitModuleSpec:
    rel_path: str
    crystallize_fn: str = "crystallize_operation"
    commit_fn: str = "commit_operation"


COMMIT_MODULE_REGISTRY: dict[GovernorDomain, CommitModuleSpec] = {
    GovernorDomain.FINANCE: CommitModuleSpec(
        rel_path="finance-governor/spine/sidecar/app/commit_ledger.py",
    ),
    GovernorDomain.INSURANCE: CommitModuleSpec(
        rel_path="insurance-governor/spine/sidecar/app/commit_ledger.py",
    ),
    GovernorDomain.CYBER: CommitModuleSpec(
        rel_path="cybersecurity-governor/spine/sidecar/app/commit_ledger.py",
    ),
}

MODEL_COMMIT_MODULE = "sidecar/app/ledger.py"
