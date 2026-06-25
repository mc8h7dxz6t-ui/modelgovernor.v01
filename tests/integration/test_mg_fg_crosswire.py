"""MG+FG cross-wire — AlgoFreeze blocks ModelGovernor reserve under shared request_id."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from gateway.app.config import Settings
from gateway.app.governance import execute_governed_dispatch


def _settings(**overrides) -> Settings:
    base = {
        "sidecar_url": "http://sidecar.test",
        "sidecar_internal_token": "test-token",
        "provider_mode": "mock",
        "algofreeze_enabled": True,
        "algofreeze_url": "http://algofreeze.test",
        "algofreeze_fail_closed": True,
        "model_runtime_sha": "approved-sha-v1",
    }
    base.update(overrides)
    return Settings(**base)


def test_reserve_blocked_when_algofreeze_frozen():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "freeze_state": "FROZEN",
        "reason": "VERSION_MISMATCH",
        "approved_sha": "approved-sha-v1",
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("gateway.app.algofreeze_guard.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        with pytest.raises(HTTPException) as exc:
            execute_governed_dispatch(
                settings=_settings(),
                user_id="u1",
                trace_id="trace-1",
                model="gpt-4o-mini",
                estimated_cost=Decimal("1.0"),
                idempotency_key="req-shared-123",
                prompt="hello",
                messages=None,
                auth_subject="test",
            )
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert detail["code"] == "ALGOFREEZE_BLOCKED"
    assert detail["request_id"] == "req-shared-123"


def test_reserve_allowed_when_algofreeze_active():
    mock_reserve = MagicMock()
    mock_reserve.status_code = 200
    mock_reserve.json.return_value = {"status": "RESERVED"}
    mock_settle = MagicMock()
    mock_settle.status_code = 200
    mock_settle.json.return_value = {"status": "SETTLED"}

    with patch("gateway.app.governance.assert_desk_active_for_reserve"):
        with patch("gateway.app.governance.httpx.Client") as gw_client:
            inst = gw_client.return_value.__enter__.return_value
            inst.post.side_effect = [mock_reserve, mock_settle]
            outcome = execute_governed_dispatch(
                settings=_settings(),
                user_id="u1",
                trace_id="trace-2",
                model="gpt-4o-mini",
                estimated_cost=Decimal("1.0"),
                idempotency_key="req-active-456",
                prompt="hello",
                messages=None,
                auth_subject="test",
            )
    assert outcome.idempotency_key == "req-active-456"
    assert outcome.reserve_status == "RESERVED"


def test_deploy_sha_mismatch_blocks_reserve():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "freeze_state": "ACTIVE",
        "approved_sha": "approved-sha-v2",
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("gateway.app.algofreeze_guard.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        with pytest.raises(HTTPException) as exc:
            execute_governed_dispatch(
                settings=_settings(model_runtime_sha="wrong-sha"),
                user_id="u1",
                trace_id="trace-3",
                model="gpt-4o-mini",
                estimated_cost=Decimal("1.0"),
                idempotency_key="req-sha-mismatch",
                prompt="hi",
                messages=None,
                auth_subject="test",
            )
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "DEPLOY_SHA_MISMATCH"
