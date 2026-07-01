"""Shared Phase C attestation validation — design-partner / VPC evidence gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_EXTERNAL_ENV_MARKERS = ("vpc", "customer", "production", "pilot-prod")
_REJECT_ENV_MARKERS = ("ci-mock", "compose-local", "embedded", "local-embedded", "local-")


def load_cluster_attestation(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing cluster attestation: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _environment_is_external(environment: str) -> bool:
    env = (environment or "").lower()
    if not env:
        return False
    if any(marker in env for marker in _REJECT_ENV_MARKERS):
        return False
    return any(marker in env for marker in _EXTERNAL_ENV_MARKERS)


def validate_cluster_attestation(data: dict[str, Any], *, min_passed: int = 7) -> list[str]:
    """Return validation errors; empty list means Phase C row is green."""
    errors: list[str] = []
    if data.get("probes_note"):
        errors.append("stub attestation (probes_note present)")
    total = int(data.get("probes_total") or 0)
    passed = int(data.get("probes_passed") or 0)
    if total <= 0:
        errors.append("no probes recorded")
    elif passed < min_passed:
        errors.append(f"insufficient probes passed: {passed}/{total} (need >= {min_passed})")
    if not data.get("artifact_sha256"):
        errors.append("missing artifact_sha256")
    probes = data.get("probes")
    if not isinstance(probes, list) or not probes:
        errors.append("missing probes list")
    environment = str(data.get("environment") or "")
    if not _environment_is_external(environment):
        errors.append(f"environment '{environment}' is not external VPC/customer evidence")
    return errors


def phase_c_valid(path: Path, *, min_passed: int = 7) -> bool:
    try:
        data = load_cluster_attestation(path)
    except (ValueError, json.JSONDecodeError):
        return False
    return not validate_cluster_attestation(data, min_passed=min_passed)
