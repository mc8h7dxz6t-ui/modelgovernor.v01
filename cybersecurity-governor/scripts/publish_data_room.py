#!/usr/bin/env python3
"""Publish committed data-room artifacts with integrity hashes."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "reliability" / "cybersecurity-governor"
PUBLISHED = ROOT / "docs" / "cybersecurity-governor" / "data-room" / "published"
DATA_ROOM = ROOT / "docs" / "cybersecurity-governor" / "data-room"
TEMPLATE = DATA_ROOM / "design-partner-signed-letter.template.md"

import sys

sys.path.insert(0, str(ROOT / "cybersecurity-governor" / "scripts"))
from attestation_validate import load_cluster_attestation, validate_cluster_attestation  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    PUBLISHED.mkdir(parents=True, exist_ok=True)

    cluster_src = ARTIFACTS / "cluster_attestation.json"
    cluster_data = load_cluster_attestation(cluster_src)
    validate_cluster_attestation(cluster_data)

    for name in ("cluster_attestation.json", "latest_attestation.json"):
        src = ARTIFACTS / name
        if src.is_file():
            dest = PUBLISHED / ("certification_attestation.json" if name == "latest_attestation.json" else name)
            shutil.copy2(src, dest)

    cluster = PUBLISHED / "cluster_attestation.json"
    cert = PUBLISHED / "certification_attestation.json"
    cluster_hash = _sha256(cluster) if cluster.is_file() else "pending"
    cert_hash = _sha256(cert) if cert.is_file() else "pending"

    redacted = DATA_ROOM / "design-partner-attestation-redacted.md"
    if redacted.is_file():
        shutil.copy2(redacted, PUBLISHED / "design-partner-attestation-redacted.md")

    pkg = DATA_ROOM / "design-partner-package.json"
    if pkg.is_file():
        shutil.copy2(pkg, PUBLISHED / "design-partner-package.json")

    if TEMPLATE.is_file():
        letter = TEMPLATE.read_text()
        letter = letter.replace("{{CLUSTER_SHA256}}", cluster_hash)
        letter = letter.replace("{{CERT_SHA256}}", cert_hash)
        letter = letter.replace(
            "{{PROBES_PASSED}}", str(cluster_data.get("probes_passed", "pending"))
        )
        letter = letter.replace(
            "{{PROBES_TOTAL}}", str(cluster_data.get("probes_total", "pending"))
        )
        letter = letter.replace("{{GENERATED_AT}}", datetime.now(timezone.utc).isoformat())
        (PUBLISHED / "design-partner-signed-letter.md").write_text(letter)

    manifest = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "completion_level": "enterprise_rehearsal_100",
        "cluster_attestation_sha256": cluster_hash,
        "certification_sha256": cert_hash,
        "probes_passed": cluster_data.get("probes_passed"),
        "probes_total": cluster_data.get("probes_total"),
        "attestation_artifact_sha256": cluster_data.get("artifact_sha256"),
        "environment": cluster_data.get("environment"),
        "files": [p.name for p in sorted(PUBLISHED.iterdir()) if p.is_file()],
    }
    (PUBLISHED / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
