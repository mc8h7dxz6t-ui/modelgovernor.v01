"""Emit portfolio maturity artifact (K2) after make plug."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spine_core.config import MATURITY_LABEL, GovernorDomain
from spine_core.il_rubric import ENGINEERING_CEILING, IL_TARGET, evaluate_portfolio

WAVE = "wave-1+3+k3+k4+m1+il-rubric"

K3_SWEEP_SEAL = "shipped"
K4_RETENTION_CRONJOB = "shipped"
H1_APPEND_LOCK = "shipped"
M1_SPINE_CONSOLIDATION = "shipped"


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def build_portfolio_self_check(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[2]
    rubric = evaluate_portfolio(root)
    governors_out: dict[str, Any] = {}
    for domain_key, data in rubric["governors"].items():
        governors_out[domain_key] = {
            "score": data["engineering_score"],
            "il_score": data["il_score"],
            "tier": data["tier"],
            "rubric_rows_green": data["rubric_rows_green"],
            "gaps_to_9": data["gaps_to_9"],
            "dimensions": data["dimensions"],
            "live_ci": data.get("live_ci", []),
        }
        if "secondary_wedges" in data:
            governors_out[domain_key]["secondary_wedges"] = data["secondary_wedges"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "maturity_label": MATURITY_LABEL,
        "wave": WAVE,
        "git_sha": _git_sha(root),
        "kernel_score": rubric["kernel_score"],
        "portfolio_score": rubric["portfolio_engineering_score"],
        "portfolio_engineering_score": rubric["portfolio_engineering_score"],
        "portfolio_il_score": rubric["portfolio_il_score"],
        "il_target": IL_TARGET,
        "engineering_ceiling": ENGINEERING_CEILING,
        "governors": governors_out,
        "path_to_9": rubric["path_to_9"],
        "k1_ledger_conformance": "spine_core.ledger_registry",
        "k3_sweep_seal": K3_SWEEP_SEAL,
        "k4_retention_cronjob": K4_RETENTION_CRONJOB,
        "h1_append_advisory_lock": H1_APPEND_LOCK,
        "m1_spine_consolidation": M1_SPINE_CONSOLIDATION,
        "note": "L5 Institutional Self-Check — IL 9/10 requires Phase C external evidence per governor.",
    }


def write_portfolio_self_check(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    payload = build_portfolio_self_check(root)
    out_dir = root / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "portfolio_self_check.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path
