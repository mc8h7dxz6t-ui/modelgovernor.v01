"""CreditGovern score gate — model version lock + reserve-before-score."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from platforms.common.event_store import AppendOnlyEventStore
from platforms.common.mesh_guard import get_mesh_guard
from platforms.common.platform_metrics import get_platform_metrics

from .exposure_ledger import ExposureLedger
from .mock_rail import MockCreditRail, ScoreResult


@dataclass(frozen=True)
class PolicyRegistry:
    approved_model_version: str
    max_auto_approve_amount: Decimal
    high_risk_threshold: Decimal = Decimal("0.7")


class ScoreGate:
    def __init__(
        self,
        ledger: ExposureLedger,
        policy: PolicyRegistry,
        rail: MockCreditRail | None = None,
    ) -> None:
        self._ledger = ledger
        self._policy = policy
        self._rail = rail or MockCreditRail()
        self._events = AppendOnlyEventStore()
        self._settled: set[str] = set()

    @property
    def events(self) -> AppendOnlyEventStore:
        return self._events

    def governed_decision(
        self,
        *,
        application_id: str,
        desk_id: str,
        exposure_amount: Decimal,
        model_version: str,
        feature_snapshot_hash: str,
    ) -> dict:
        metrics = get_platform_metrics()

        mesh_ok, mesh_reason = get_mesh_guard().allows_credit_score()
        if not mesh_ok:
            metrics.increment("reserve_before_score_blocked_total")
            return {"status": "BLOCKED", "reason": mesh_reason}

        if model_version != self._policy.approved_model_version:
            metrics.increment("model_version_mismatch_total")
            return {"status": "BLOCKED", "reason": "MODEL_VERSION_MISMATCH"}

        if application_id in self._settled:
            return {"status": "DUPLICATE", "application_id": application_id}

        ok, reason = self._ledger.reserve(desk_id, exposure_amount)
        if not ok:
            if reason == "INSUFFICIENT_EXPOSURE":
                metrics.increment("exposure_cap_overrun_total")
            if reason == "NEGATIVE_BALANCE":
                metrics.increment("negative_balance_detected_total")
            metrics.increment("reserve_before_score_blocked_total")
            return {"status": "DENIED", "reason": reason}

        score = self._rail.score(feature_snapshot_hash=feature_snapshot_hash)
        if exposure_amount > self._policy.max_auto_approve_amount:
            self._ledger.refund_reserve(desk_id, exposure_amount)
            return {"status": "APPROVAL_REQUIRED", "score": score.score, "risk_tier": score.risk_tier}

        if score.risk_tier == "high":
            self._ledger.refund_reserve(desk_id, exposure_amount)
            metrics.increment("high_risk_auto_expired_total")
            return {"status": "STRANDED", "score": score.score, "reason": "HIGH_RISK"}

        outcome = "APPROVED" if score.score >= Decimal("0.5") else "DENIED"
        if outcome == "DENIED":
            self._ledger.refund_reserve(desk_id, exposure_amount)

        self._settled.add(application_id)
        self._events.append(
            platform="credit_govern",
            event_type="SETTLED",
            operation_id=application_id,
            payload={
                "outcome": outcome,
                "score": str(score.score),
                "model_version": model_version,
                "exposure_amount": str(exposure_amount),
                "explanation_id": score.explanation_id,
            },
        )
        return {
            "status": "SETTLED",
            "outcome": outcome,
            "score": str(score.score),
            "explanation_id": score.explanation_id,
            "application_id": application_id,
        }
