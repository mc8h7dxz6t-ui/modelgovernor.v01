"""Security chain anchor S3 tests."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from app.config import Settings
from app.metrics import get_counters
from app.security_anchor_s3 import anchor_head_to_s3


def test_anchor_head_to_s3_uses_object_lock_when_enabled() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://example/0",
        cg_internal_tokens="token",
        security_anchor_s3_bucket="security-audit-bucket",
        security_anchor_s3_prefix="anchors",
        security_anchor_s3_region="us-east-1",
        security_anchor_s3_object_lock_enabled=True,
        security_anchor_s3_object_lock_mode="GOVERNANCE",
        security_anchor_s3_retention_days=365,
    )
    mock_client = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client

    with patch("app.security_anchor_s3.get_settings", return_value=settings):
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = anchor_head_to_s3(
                head_hash="a" * 64,
                sealed_count=10,
                total_events=12,
                source="test",
                first_event_id=1,
                last_event_id=12,
            )

    assert result["s3_anchored"] is True
    assert result["s3_key"] == f"anchors/{'a' * 64}.json"
    put_kwargs = mock_client.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "security-audit-bucket"
    assert put_kwargs["ObjectLockMode"] == "GOVERNANCE"
    assert get_counters().snapshot().get("security_chain_anchor_s3_ok_total", 0) >= 1
