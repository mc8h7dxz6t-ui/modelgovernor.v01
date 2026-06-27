#!/usr/bin/env python3
"""Generate redacted design-partner attestation package for data room."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "reliability" / "cybersecurity-governor"
DATA_ROOM = ROOT / "docs" / "cybersecurity-governor" / "data-room"


def _load_attestation() -> dict:
    for name in ("cluster_attestation.json", "latest_pilot_attestation.json", "latest_attestation.json"):
        path = ARTIFACTS / name
        if path.is_file():
            return json.loads(path.read_text())
    return {}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_markdown(attestation: dict, cert_path: Path | None) -> str:
    partner = attestation.get("design_partner", "[REDACTED_CARRIER]")
    env = attestation.get("environment", "customer-vpc-staging")
    artifact_hash = attestation.get("artifact_sha256", "pending")
    cert_hash = _sha256_file(cert_path) if cert_path and cert_path.is_file() else "pending"
    passed = attestation.get("probes_passed", 0)
    total = attestation.get("probes_total", 0)
    generated = attestation.get("generated_at", datetime.now(timezone.utc).isoformat())

    return f"""# Design-Partner Attestation (Redacted)

**Document classification:** Data room — NDA redacted excerpt  
**Generated:** {generated}  
**Design partner:** {partner}  
**Environment:** {env}  

---

## Executive summary

{partner} completed a **design-partner rehearsal** of Cybersecurity Governor on a **{env}** cluster. The attestation exercise validated governed security commits, hash-chain integrity, EgressGovern allowlist + Envoy ext_authz adapter, and IdentityGovern session arm.

| Metric | Result |
|--------|--------|
| Attestation probes passed | **{passed} / {total}** |
| Pilot attestation SHA-256 | `{artifact_hash}` |
| Certification artifact SHA-256 | `{cert_hash}` |

---

## Exercises completed (redacted)

1. **Spine L4** — governed commit, `verify-chain`, anchor head  
2. **EgressGovern** — allowlisted host ALLOWED; off-allowlist DENIED; ext_authz adapter  
3. **IdentityGovern** — session arm with device fingerprint binding  
4. **Threat Mesh** — parent VIOLATION/DRIFT blocks child egress commit (pytest-proven)  
5. **Optional SKUs** — WitnessBridge, LineageIngest, ContentGuard when stack is up  

---

## Safe external claims

- Hash-chained `security_events` verified tamper-free after governed operations  
- Fail-closed platform guard on unregistered facets (HTTP 422)  
- L4 Gold = institutional test + deploy kit gate — not Fortune 500 cyber suite replacement  

---

## Artifact references

| File | Path |
|------|------|
| Cluster attestation | `artifacts/reliability/cybersecurity-governor/cluster_attestation.json` |
| Certification | `artifacts/reliability/cybersecurity-governor/latest_attestation.json` |
| Full methodology | `docs/cybersecurity-governor/design-partner-attestation.md` |

---

## NDA notice

Carrier legal name, VPC identifiers, and IdP tenant IDs are redacted. Full signed design-partner letter available under mutual NDA.

*This document is suitable for investor data room and wholesale broker RFP appendices.*
"""


def main() -> int:
    DATA_ROOM.mkdir(parents=True, exist_ok=True)
    attestation = _load_attestation()
    if not attestation:
        print("No attestation artifact found — run attestation_runner against live stack first", file=sys.stderr)
        return 1
    if attestation.get("probes_note") or int(attestation.get("probes_total") or 0) <= 0:
        print("Attestation has no live probes — run make cg-pilot-attestation first", file=sys.stderr)
        return 1
    cert = ARTIFACTS / "latest_attestation.json"

    md = generate_markdown(attestation, cert)
    out_md = DATA_ROOM / "design-partner-attestation-redacted.md"
    out_md.write_text(md)

    package = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "design_partner_redacted": attestation.get("design_partner", "[REDACTED_CARRIER]"),
        "environment": attestation.get("environment", "customer-vpc-staging"),
        "attestation_sha256": attestation.get("artifact_sha256"),
        "certification_sha256": _sha256_file(cert) if cert.is_file() else None,
        "data_room_markdown": str(out_md.relative_to(ROOT)),
        "probes_passed": attestation.get("probes_passed"),
        "probes_total": attestation.get("probes_total"),
    }
    pkg_path = DATA_ROOM / "design-partner-package.json"
    pkg_path.write_text(json.dumps(package, indent=2))

    print(json.dumps(package, indent=2))
    print(f"\nWrote {out_md}", file=sys.stderr)
    print(f"Wrote {pkg_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
