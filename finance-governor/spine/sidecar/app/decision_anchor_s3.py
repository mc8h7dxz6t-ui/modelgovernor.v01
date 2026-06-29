"""S3 Object Lock external anchor for verified decision chain heads."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import get_settings
from .metrics import get_counters

logger = logging.getLogger(__name__)


def anchor_head_to_s3(
    *,
    head_hash: str,
    sealed_count: int,
    total_events: int,
    source: str,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.decision_anchor_s3_bucket:
        return {"s3_anchored": False, "reason": "s3 bucket not configured"}

    try:
        import boto3
    except ImportError:
        get_counters().increment("decision_chain_anchor_s3_failed_total")
        return {"s3_anchored": False, "reason": "boto3 unavailable"}

    payload = {
        "head_hash": head_hash,
        "sealed_count": sealed_count,
        "total_events": total_events,
        "source": source,
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "product": "finance-governor",
    }
    key = f"{settings.decision_anchor_s3_prefix.rstrip('/')}/{head_hash}.json"
    client_kwargs: dict[str, Any] = {}
    if settings.decision_anchor_s3_region:
        client_kwargs["region_name"] = settings.decision_anchor_s3_region
    if settings.decision_anchor_s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.decision_anchor_s3_endpoint_url

    client = boto3.client("s3", **client_kwargs)
    put_kwargs: dict[str, Any] = {
        "Bucket": settings.decision_anchor_s3_bucket,
        "Key": key,
        "Body": json.dumps(payload, sort_keys=True).encode("utf-8"),
        "ContentType": "application/json",
        "Metadata": {"head-hash": head_hash, "sealed-count": str(sealed_count), "source": source},
    }
    if settings.decision_anchor_s3_object_lock_enabled:
        retain_until = datetime.now(timezone.utc) + timedelta(days=settings.decision_anchor_s3_retention_days)
        put_kwargs["ObjectLockMode"] = settings.decision_anchor_s3_object_lock_mode
        put_kwargs["ObjectLockRetainUntilDate"] = retain_until

    try:
        client.put_object(**put_kwargs)
    except Exception as exc:
        logger.warning("fg decision anchor s3 failed bucket=%s key=%s: %s", settings.decision_anchor_s3_bucket, key, exc)
        get_counters().increment("decision_chain_anchor_s3_failed_total")
        return {"s3_anchored": False, "reason": str(exc), "s3_key": key}

    get_counters().increment("decision_chain_anchor_s3_ok_total")
    return {
        "s3_anchored": True,
        "s3_bucket": settings.decision_anchor_s3_bucket,
        "s3_key": key,
        "object_lock": settings.decision_anchor_s3_object_lock_enabled,
    }
