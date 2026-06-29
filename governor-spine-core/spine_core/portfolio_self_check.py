"""Emit portfolio maturity artifact (K2) after make plug."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spine_core.config import MATURITY_LABEL, GovernorDomain

WAVE = "wave-1+3+k3"

GOVERNOR_SCORES: dict[str, dict[str, Any]] = {
    GovernorDomain.MODEL.value: {
        "score": 7.5,
        "tier": "L5",
        "live_ci": ["compose-smoke-mg", "mg-pilot-attestation"],
    },
    GovernorDomain.FINANCE.value: {
        "score": 7.0,
        "tier": "L5",
        "live_ci": ["compose-smoke-fg", "fg-pilot-attestation"],
    },
    GovernorDomain.CYBER.value: {
        "score": 8.5,
        "tier": "L5",
        "live_ci": ["compose-smoke-cg", "cg-pilot-attestation"],
    },
    GovernorDomain.INSURANCE.value: {
        "score": 8.0,
        "tier": "L5",
        "live_ci": ["compose-smoke-ig", "ig-pilot-attestation"],
        "secondary_wedges": {"spatial_twin": 7.5, "subrogation_graph": 7.5},
    },
}

KERNEL_SCORE = 8.5
PORTFOLIO_SCORE = 7.5
K3_SWEEP_SEAL = "shipped"


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def build_portfolio_self_check(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[2]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "maturity_label": MATURITY_LABEL,
        "wave": WAVE,
        "git_sha": _git_sha(root),
        "kernel_score": KERNEL_SCORE,
        "portfolio_score": PORTFOLIO_SCORE,
        "governors": GOVERNOR_SCORES,
        "k1_ledger_conformance": "spine_core.ledger_registry",
        "k3_sweep_seal": K3_SWEEP_SEAL,
        "note": "L5 Institutional Self-Check — not SOC 2 or third-party audit certification.",
    }


def write_portfolio_self_check(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    payload = build_portfolio_self_check(root)
    out_dir = root / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "portfolio_self_check.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path
