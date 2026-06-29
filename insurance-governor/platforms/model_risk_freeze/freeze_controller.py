"""Model risk freeze controller — E&O / Cyber catastrophic model failure prevention."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class FreezeState(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    DEGRADED = "DEGRADED"


@dataclass
class VersionRegistry:
    approved_version: str
    product_line: str = "claims_triage"

    def check(self, runtime_version: str) -> bool:
        return runtime_version.strip() == self.approved_version.strip()


@dataclass
class ModelRiskController:
    state: FreezeState = FreezeState.ACTIVE
    reason: str | None = None
    frozen_at: datetime | None = None
    blocked_inferences: int = 0

    def freeze(self, reason: str) -> None:
        self.state = FreezeState.FROZEN
        self.reason = reason
        self.frozen_at = datetime.now(timezone.utc)

    def unfreeze(self) -> None:
        self.state = FreezeState.ACTIVE
        self.reason = None
        self.frozen_at = None

    def allow_inference(self) -> bool:
        if self.state == FreezeState.FROZEN:
            self.blocked_inferences += 1
            return False
        return True


@dataclass
class InferenceEvaluation:
    allowed: bool
    decision: str
    freeze_state: str
    reason: str | None = None


def evaluate_inference(
    *,
    inference_id: str,
    runtime_version: str,
    registry: VersionRegistry,
    controller: ModelRiskController,
    jurisdiction: str = "US",
) -> InferenceEvaluation:
    if not registry.check(runtime_version):
        controller.freeze(reason="MODEL_VERSION_DRIFT")
        return InferenceEvaluation(
            False,
            "FROZEN",
            FreezeState.FROZEN.value,
            f"version_mismatch:{runtime_version}!={registry.approved_version}",
        )

    if not controller.allow_inference():
        return InferenceEvaluation(
            False,
            "FROZEN",
            FreezeState.FROZEN.value,
            controller.reason or "desk_frozen",
        )

    return InferenceEvaluation(True, "ACTIVE", FreezeState.ACTIVE.value)
