"""Re-export horizon sweep from sidecar (single source of truth)."""
from __future__ import annotations

import sys
from pathlib import Path

_SIDECAR = Path(__file__).resolve().parents[2] / "sidecar"
if str(_SIDECAR) not in sys.path:
    sys.path.insert(0, str(_SIDECAR))

from app.horizon_sweep import sweep_expired_horizons  # noqa: E402

__all__ = ["sweep_expired_horizons"]
