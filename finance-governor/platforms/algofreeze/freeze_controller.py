"""AlgoFreeze — version guard and freeze state machine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FreezeState(str, Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    FROZEN = "FROZEN"


@dataclass
class VersionRegistry:
    approved_sha: str

    def check(self, runtime_sha: str) -> bool:
        return runtime_sha == self.approved_sha


class FreezeController:
    def __init__(self) -> None:
        self._state = FreezeState.ACTIVE
        self._reason: str | None = None

    @property
    def state(self) -> FreezeState:
        return self._state

    @property
    def reason(self) -> str | None:
        return self._reason

    def freeze(self, reason: str) -> None:
        self._state = FreezeState.FROZEN
        self._reason = reason

    def degrade(self, reason: str) -> None:
        if self._state != FreezeState.FROZEN:
            self._state = FreezeState.DEGRADED
            self._reason = reason

    def unfreeze(self) -> None:
        self._state = FreezeState.ACTIVE
        self._reason = None

    def allows_egress(self) -> bool:
        return self._state == FreezeState.ACTIVE
