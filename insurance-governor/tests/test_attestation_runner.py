"""Attestation runner unit tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_runner():
    path = Path(__file__).resolve().parents[1] / "scripts" / "attestation_runner.py"
    spec = importlib.util.spec_from_file_location("attestation_runner", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_write_artifacts_includes_sha256(tmp_path, monkeypatch):
    mod = _load_runner()
    monkeypatch.setattr(mod, "ARTIFACTS", tmp_path)
    report = {"attestation_type": "pilot", "probes_passed": 5, "probes_total": 5}
    path = mod.write_artifacts(report)
    data = json.loads(path.read_text())
    assert "artifact_sha256" in data
    assert len(data["artifact_sha256"]) == 64


def test_run_attestation_offline_records_failures(monkeypatch):
    mod = _load_runner()

    def boom(*_a, **_k):
        raise OSError("connection refused")

    monkeypatch.setattr(mod, "_get", boom)
    report = mod.run_attestation()
    assert report["probes_failed"] >= 1
