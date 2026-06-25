#!/usr/bin/env python3
"""Publish committed data-room artifacts with integrity hashes."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "reliability" / "insurance-governor"
PUBLISHED = ROOT / "docs" / "insurance-governor" / "data-room" / "published"
TEMPLATE = ROOT / "docs" / "insurance-governor" / "data-room" / "design-partner-signed-letter.template.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    PUBLISHED.mkdir(parents=True, exist_ok=True)

    for name in ("cluster_attestation.json", "latest_attestation.json"):
        src = ARTIFACTS / name
        if src.is_file():
            dest = PUBLISHED / ("certification_attestation.json" if name == "latest_attestation.json" else name)
            shutil.copy2(src, dest)

    cluster = PUBLISHED / "cluster_attestation.json"
    cert = PUBLISHED / "certification_attestation.json"
    cluster_hash = _sha256(cluster) if cluster.is_file() else "pending"
    cert_hash = _sha256(cert) if cert.is_file() else "pending"

    if TEMPLATE.is_file():
        letter = TEMPLATE.read_text()
        letter = letter.replace("{{CLUSTER_SHA256}}", cluster_hash)
        letter = letter.replace("{{CERT_SHA256}}", cert_hash)
        letter = letter.replace("{{GENERATED_AT}}", datetime.now(timezone.utc).isoformat())
        (PUBLISHED / "design-partner-signed-letter.md").write_text(letter)

    manifest = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "completion_level": "enterprise_rehearsal_100",
        "cluster_attestation_sha256": cluster_hash,
        "certification_sha256": cert_hash,
        "files": [p.name for p in sorted(PUBLISHED.iterdir()) if p.is_file()],
    }
    (PUBLISHED / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
