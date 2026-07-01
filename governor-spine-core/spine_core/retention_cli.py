"""CLI entrypoint for K4 retention CronJobs."""

from __future__ import annotations

import argparse
import json
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spine_core.config import GovernorDomain
from spine_core.retention_runner import run_retention


def _parse_domain(raw: str) -> GovernorDomain:
    normalized = raw.strip().upper().replace("-", "_")
    aliases = {
        "MODEL": GovernorDomain.MODEL,
        "MG": GovernorDomain.MODEL,
        "MODEL_GOVERNOR": GovernorDomain.MODEL,
        "FINANCE": GovernorDomain.FINANCE,
        "FG": GovernorDomain.FINANCE,
        "FINANCE_GOVERNOR": GovernorDomain.FINANCE,
        "INSURANCE": GovernorDomain.INSURANCE,
        "IG": GovernorDomain.INSURANCE,
        "INSURANCE_GOVERNOR": GovernorDomain.INSURANCE,
        "CYBER": GovernorDomain.CYBER,
        "CG": GovernorDomain.CYBER,
        "CYBER_GOVERNOR": GovernorDomain.CYBER,
    }
    if normalized not in aliases:
        raise argparse.ArgumentTypeError(f"unknown governor domain: {raw}")
    return aliases[normalized]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run governor ledger retention tiers (K4).")
    parser.add_argument("--domain", required=True, type=_parse_domain)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="SQLAlchemy database URL (default: DATABASE_URL env)",
    )
    args = parser.parse_args(argv)

    if not args.database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    engine = create_engine(args.database_url, future=True)
    with Session(engine) as session:
        report = run_retention(session, args.domain)
        session.commit()
        print(json.dumps(report.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
