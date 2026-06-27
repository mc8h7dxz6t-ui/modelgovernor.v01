"""Validate attestation artifacts before data-room publish."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "reliability" / "cybersecurity-governor"


def load_cluster_attestation(path: Path | None = None) -> dict[str, Any]:
    target = path or (ARTIFACTS / "cluster_attestation.json")
    if not target.is_file():
        raise SystemExit(f"missing cluster attestation: {target}")
    return json.loads(target.read_text())


def validate_cluster_attestation(data: dict[str, Any], *, min_passed: int = 7) -> None:
    if data.get("probes_note"):
        raise SystemExit("cluster attestation is a stub (probes_note present) — run make cg-pilot-attestation")
    total = int(data.get("probes_total") or 0)
    passed = int(data.get("probes_passed") or 0)
    if total <= 0:
        raise SystemExit("cluster attestation has no probes — run attestation_runner against live stack")
    if passed < min_passed:
        raise SystemExit(f"insufficient probes passed: {passed}/{total} (need >= {min_passed})")
    if not data.get("artifact_sha256"):
        raise SystemExit("cluster attestation missing artifact_sha256")
    probes = data.get("probes")
    if not isinstance(probes, list) or not probes:
        raise SystemExit("cluster attestation missing probes list")


def main() -> int:
    data = load_cluster_attestation()
    validate_cluster_attestation(data)
    print(
        json.dumps(
            {
                "valid": True,
                "probes_passed": data.get("probes_passed"),
                "probes_total": data.get("probes_total"),
                "artifact_sha256": data.get("artifact_sha256"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
