"""ContentGuard platform tests."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.content_guard.content_policy import evaluate_content  # noqa: E402
from platforms.content_guard.main import app  # noqa: E402


def test_content_allowed_clean():
    client = TestClient(app)
    r = client.post(
        "/content/evaluate",
        json={
            "content_id": "c1",
            "principal_id": "alice@corp.example",
            "channel": "publish",
            "text_body": "Quarterly earnings summary for internal review.",
            "classification_hint": "internal",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOWED"


def test_content_blocked_ssn():
    client = TestClient(app)
    r = client.post(
        "/content/evaluate",
        json={
            "content_id": "c2",
            "principal_id": "alice@corp.example",
            "text_body": "Employee SSN 123-45-6789 attached.",
            "classification_hint": "restricted",
        },
    )
    body = r.json()
    assert body["decision"] == "BLOCKED"
    assert "pii_ssn" in body["matched_patterns"]


def test_content_redacted_pan():
    result = evaluate_content(
        text_body="Card 4111-1111-1111-1111 for refund",
        channel="email",
        classification_hint="internal",
        principal_id="alice@corp.example",
    )
    assert result.decision == "REDACTED"
    assert result.redacted_body is not None
    assert "[REDACTED:pii_pan]" in result.redacted_body
