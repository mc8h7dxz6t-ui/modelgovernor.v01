#!/usr/bin/env python3
"""Generate institutional++ invariant report for Cyber Governor."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(ROOT))

from tests.helpers import cg_settings, create_sqlite_engine, identity_facets, session_factory  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "report.sqlite3"
        engine = create_sqlite_engine(db_path)
        settings = cg_settings(str(engine.url))

        from app.commit_ledger import commit_operation, crystallize_operation
        from app.security_seal import verify_security_chain

        facets = identity_facets()
        Session = session_factory(engine)
        with Session() as s:
            cr = crystallize_operation(
                s,
                settings,
                platform="identity_gate",
                operation_id="report-probe",
                account_id="tenant-default",
                risk_tier="critical",
                facets=facets,
                policy_id="identity-critical-us",
            )
            crystal_id = cr.crystal_id
        with Session() as s:
            commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")
        with Session() as s:
            chain = verify_security_chain(s)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_url_redacted": "sqlite",
        "security_chain": chain.to_dict(),
        "invariants": {
            "hash_chain_ok": chain.valid,
            "events_verified": chain.sealed_count,
            "head_hash": chain.head_hash,
        },
        "status": "PASS" if chain.valid else "FAIL",
    }

    out = ROOT / "reports" / "cyber-invariant-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
