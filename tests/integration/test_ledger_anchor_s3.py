"""S3 Object Lock ledger anchor tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sidecar.app.config import Settings
from sidecar.app.ledger_anchor_s3 import anchor_head_to_s3
from sidecar.app.metrics import get_counters


def test_anchor_head_to_s3_uses_object_lock_when_enabled() -> None:
    pytest.importorskip("boto3")
    settings = Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://example/0",
        sidecar_internal_tokens="token",
        ledger_anchor_s3_bucket="audit-bucket",
        ledger_anchor_s3_prefix="anchors",
        ledger_anchor_s3_region="us-east-1",
        ledger_anchor_s3_object_lock_enabled=True,
        ledger_anchor_s3_object_lock_mode="GOVERNANCE",
        ledger_anchor_s3_retention_days=365,
    )
    mock_client = MagicMock()
    get_counters().reset()

    with patch("sidecar.app.ledger_anchor_s3.get_settings", return_value=settings):
        with patch("boto3.client", return_value=mock_client):
            result = anchor_head_to_s3(
                head_hash="a" * 64,
                sealed_count=10,
                total_events=12,
                source="test",
            )

    assert result["s3_anchored"] is True
    assert result["s3_key"] == f"anchors/{'a' * 64}.json"
    put_kwargs = mock_client.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "audit-bucket"
    assert put_kwargs["ObjectLockMode"] == "GOVERNANCE"
    assert "ObjectLockRetainUntilDate" in put_kwargs
    assert get_counters().snapshot()["ledger_chain_anchor_s3_ok_total"] == 1


def test_anchor_head_to_s3_skips_without_bucket() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://example/0",
        sidecar_internal_tokens="token",
    )
    with patch("sidecar.app.ledger_anchor_s3.get_settings", return_value=settings):
        result = anchor_head_to_s3(
            head_hash="b" * 64,
            sealed_count=1,
            total_events=1,
            source="test",
        )
    assert result["s3_anchored"] is False
