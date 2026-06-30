"""Emit portfolio maturity artifact (K2) after make plug."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spine_core.config import MATURITY_LABEL
from spine_core.il_rubric import ENGINEERING_CEILING, IL_TARGET, _kernel_score, evaluate_portfolio

WAVE = "wave-1+3+k3+k4+m1+il-rubric"


def _kernel_conformance_labels(root: Path) -> dict[str, str]:
    from spine_core.append_lock import append_lock_conformance_failures
    from spine_core.ledger_registry import conformance_failures
    from spine_core.m1_conformance import m1_conformance_failures
    from spine_core.retention_cronjob import retention_cronjob_conformance_failures
    from spine_core.sweep_seal import sweep_conformance_failures

    def _label(failures: list[str]) -> str:
        return "shipped" if not failures else "gap"

    return {
        "k1_ledger_conformance": _label(conformance_failures(root)),
        "k3_sweep_seal": _label(sweep_conformance_failures(root)),
        "h1_append_advisory_lock": _label(append_lock_conformance_failures(root)),
        "k4_retention_cronjob": _label(retention_cronjob_conformance_failures(root)),
        "m1_spine_consolidation": _label(m1_conformance_failures(root)),
    }


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def build_portfolio_self_check(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[2]
    rubric = evaluate_portfolio(root)
    kernel_labels = _kernel_conformance_labels(root)
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
        "k1_ledger_conformance": kernel_labels["k1_ledger_conformance"],
        "k3_sweep_seal": kernel_labels["k3_sweep_seal"],
        "k4_retention_cronjob": kernel_labels["k4_retention_cronjob"],
        "h1_append_advisory_lock": kernel_labels["h1_append_advisory_lock"],
        "m1_spine_consolidation": kernel_labels["m1_spine_consolidation"],
        "kernel_score_verified": _kernel_score(root) == rubric["kernel_score"],
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
