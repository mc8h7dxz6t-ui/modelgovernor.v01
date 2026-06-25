"""S3 Object Lock claim anchor tests."""
from __future__ import annotations

import sys
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from app.claim_anchor_s3 import anchor_head_to_s3
from app.config import Settings
from app.metrics import get_counters


def test_anchor_head_to_s3_uses_object_lock_when_enabled() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://example/0",
        ig_internal_tokens="token",
        claim_anchor_s3_bucket="ig-audit-bucket",
        claim_anchor_s3_prefix="anchors",
        claim_anchor_s3_region="us-east-1",
        claim_anchor_s3_object_lock_enabled=True,
        claim_anchor_s3_object_lock_mode="GOVERNANCE",
        claim_anchor_s3_retention_days=365,
    )
    mock_client = MagicMock()

    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client

    with patch("app.claim_anchor_s3.get_settings", return_value=settings):
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = anchor_head_to_s3(
                head_hash="a" * 64,
                sealed_count=10,
                total_events=12,
                source="test",
            )

    assert result["s3_anchored"] is True
    assert result["s3_key"] == f"anchors/{'a' * 64}.json"
    put_kwargs = mock_client.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "ig-audit-bucket"
    assert put_kwargs["ObjectLockMode"] == "GOVERNANCE"
    assert "ObjectLockRetainUntilDate" in put_kwargs
    assert get_counters().snapshot().get("claim_chain_anchor_s3_ok_total", 0) >= 1


def test_anchor_head_to_s3_skips_without_bucket() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://example/0",
        ig_internal_tokens="token",
    )
    with patch("app.claim_anchor_s3.get_settings", return_value=settings):
        result = anchor_head_to_s3(
            head_hash="b" * 64,
            sealed_count=1,
            total_events=1,
            source="test",
        )
    assert result["s3_anchored"] is False
