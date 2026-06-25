"""Reconciler test helpers — load modules without clashing with sidecar `app` package."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_reconciler_module(name: str):
    path = ROOT / "spine" / "reconciler" / "app" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"ig_reconciler_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load reconciler module: {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
