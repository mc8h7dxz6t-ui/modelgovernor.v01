"""Session binding evaluation — identity/session hijack strand semantics."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionProfile:
    user_id: str
    expected_device_fingerprint: str
    expected_ip_prefix: str | None = None


@dataclass(frozen=True)
class SessionEvaluation:
    approved: bool
    session_state: str
    reason: str | None
    binding_score: float


def evaluate_session(
    *,
    user_id: str,
    device_fingerprint: str,
    client_ip: str,
    profile: SessionProfile,
) -> SessionEvaluation:
    if user_id != profile.user_id:
        return SessionEvaluation(False, "STRANDED", "user_id mismatch", 0.0)

    fingerprint_match = device_fingerprint == profile.expected_device_fingerprint
    ip_ok = True
    if profile.expected_ip_prefix:
        ip_ok = client_ip.startswith(profile.expected_ip_prefix)

    if fingerprint_match and ip_ok:
        return SessionEvaluation(True, "AUTHORIZED", None, 1.0)

    reasons: list[str] = []
    if not fingerprint_match:
        reasons.append("device_fingerprint mismatch")
    if not ip_ok:
        reasons.append("ip_prefix mismatch")
    return SessionEvaluation(False, "STRANDED", "; ".join(reasons), 0.2 if ip_ok else 0.0)
