"""Validate attestation artifacts before data-room publish — delegates to spine_core."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SPINE_CORE = ROOT / "governor-spine-core"
if str(SPINE_CORE) not in sys.path:
    sys.path.insert(0, str(SPINE_CORE))

from spine_core.attestation_validate import validate_cluster_attestation as _validate  # noqa: E402

ARTIFACTS = ROOT / "artifacts" / "reliability" / "cybersecurity-governor"


def validate_cluster_attestation(data: dict[str, Any], *, min_passed: int = 7) -> None:
    errors = _validate(data, min_passed=min_passed)
    if errors:
        raise SystemExit("; ".join(errors))


def load_cluster_attestation(path: Path | None = None) -> dict[str, Any]:
    target = path or (ARTIFACTS / "cluster_attestation.json")
    if not target.is_file():
        raise SystemExit(f"missing cluster attestation: {target}")
    return json.loads(target.read_text())


def main() -> int:
    data = load_cluster_attestation()
    errors = validate_cluster_attestation(data)
    if errors:
        raise SystemExit("; ".join(errors))
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
