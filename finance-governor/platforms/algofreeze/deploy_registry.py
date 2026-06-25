"""CI/CD deploy SHA registry — version/feed-aware kill switch vs exchange blunt halt."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DeployRecord:
    sha: str
    approved_by: str
    approved_at: str
    ci_pipeline_id: str
    environment: str


@dataclass
class DeployRegistry:
    """Approved deploy SHA registry (EMS/CI integration point)."""

    environment: str = "production"
    _approved: DeployRecord | None = None
    _history: list[DeployRecord] = field(default_factory=list)

    @property
    def approved_sha(self) -> str | None:
        return self._approved.sha if self._approved else None

    def register_approval(
        self,
        sha: str,
        *,
        approved_by: str = "ci-pipeline",
        ci_pipeline_id: str = "local",
    ) -> DeployRecord:
        record = DeployRecord(
            sha=sha,
            approved_by=approved_by,
            approved_at=datetime.now(timezone.utc).isoformat(),
            ci_pipeline_id=ci_pipeline_id,
            environment=self.environment,
        )
        self._approved = record
        self._history.append(record)
        return record

    def check_runtime(self, runtime_sha: str) -> tuple[bool, str | None]:
        if self._approved is None:
            return False, "NO_APPROVED_DEPLOY"
        if runtime_sha != self._approved.sha:
            return False, "VERSION_MISMATCH"
        return True, None

    def history(self, limit: int = 20) -> list[DeployRecord]:
        return list(self._history[-limit:])
