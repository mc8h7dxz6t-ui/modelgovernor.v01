"""Posture baseline evaluation — reconcile live scan vs approved crystal."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PostureBaseline:
    baseline_id: str
    min_posture_score: int
    critical_controls: frozenset[str]


@dataclass(frozen=True)
class PostureEvaluation:
    approved: bool
    decision: str
    posture_state: str
    drift_score: float
    reason: str | None


def evaluate_posture(
    *,
    posture_score: int,
    failed_controls: list[str],
    baseline: PostureBaseline,
) -> PostureEvaluation:
    failed = {c.strip().lower() for c in failed_controls if c.strip()}
    critical = {c.lower() for c in baseline.critical_controls}
    critical_hits = failed & critical

    drift_score = max(0.0, min(1.0, (100 - posture_score) / 100.0))

    if posture_score < baseline.min_posture_score:
        return PostureEvaluation(
            False,
            "STRANDED",
            "STRANDED",
            drift_score,
            f"posture_score {posture_score} below minimum {baseline.min_posture_score}",
        )

    if critical_hits:
        return PostureEvaluation(
            False,
            "STRANDED",
            "STRANDED",
            drift_score,
            f"critical controls failed: {', '.join(sorted(critical_hits))}",
        )

    if failed:
        return PostureEvaluation(
            False,
            "REMEDIATE",
            "DRIFT",
            drift_score,
            f"non-critical drift: {', '.join(sorted(failed))}",
        )

    return PostureEvaluation(True, "ALLOWED", "COMPLIANT", drift_score, None)
