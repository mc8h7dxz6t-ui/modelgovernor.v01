"""Settings auto-config for production zero-friction."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from app.config import Settings


def test_s3_object_lock_auto_enabled_when_bucket_set():
    s = Settings(
        database_url="sqlite://",
        security_anchor_s3_bucket="corp-anchor-bucket",
        security_anchor_s3_object_lock_enabled=False,
        _env_file=None,
    )
    assert s.security_anchor_s3_object_lock_enabled is True


def test_s3_object_lock_respects_explicit_disable_with_bucket():
    s = Settings(
        database_url="sqlite://",
        security_anchor_s3_bucket="corp-anchor-bucket",
        security_anchor_s3_object_lock_enabled=True,
        _env_file=None,
    )
    assert s.security_anchor_s3_object_lock_enabled is True


def test_no_bucket_keeps_object_lock_off(monkeypatch):
    monkeypatch.delenv("SECURITY_ANCHOR_S3_BUCKET", raising=False)
    s = Settings(
        database_url="sqlite://",
        security_anchor_s3_bucket=None,
        _env_file=None,
    )
    assert s.security_anchor_s3_object_lock_enabled is False
