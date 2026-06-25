"""Live inference rail tests."""
from __future__ import annotations

import threading
from decimal import Decimal

import pytest
import uvicorn

from platforms.credit_govern.inference_rail import InferenceRailClient, RailConfig, reset_inference_rail
from platforms.credit_govern.rail_server import app as rail_app


@pytest.fixture()
def live_rail_server():
    config = uvicorn.Config(rail_app, host="127.0.0.1", port=18797, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            break
        import time

        time.sleep(0.05)
    yield "http://127.0.0.1:18797"
    server.should_exit = True


def test_mock_mode_unchanged():
    reset_inference_rail()
    client = InferenceRailClient(RailConfig(mode="mock"))
    outcome = client.score(
        application_id="app-1",
        exposure=Decimal("1000"),
        model_version_id="credit-model-v3",
    )
    assert outcome.decision == "APPROVE"


def test_live_http_rail(live_rail_server):
    reset_inference_rail()
    client = InferenceRailClient(RailConfig(mode="live", url=live_rail_server, timeout_s=5))
    outcome = client.score(
        application_id="app-live-1",
        exposure=Decimal("50000"),
        model_version_id="credit-model-v3",
    )
    assert outcome.decision == "APPROVE"
    assert outcome.explanation_id.startswith("exp-rail")


def test_auto_fallback_when_rail_down():
    reset_inference_rail()
    client = InferenceRailClient(
        RailConfig(mode="auto", url="http://127.0.0.1:1", timeout_s=0.5, circuit_threshold=1)
    )
    outcome = client.score(
        application_id="app-auto-1",
        exposure=Decimal("1000"),
        model_version_id="credit-model-v3",
    )
    assert outcome.decision == "APPROVE"


def test_circuit_opens_in_live_mode():
    reset_inference_rail()
    client = InferenceRailClient(
        RailConfig(mode="live", url="http://127.0.0.1:1", timeout_s=0.2, circuit_threshold=1)
    )
    with pytest.raises(Exception):
        client.score(
            application_id="app-circuit",
            exposure=Decimal("1000"),
            model_version_id="credit-model-v3",
        )
    assert client.circuit_open


def test_sagemaker_response_parse():
    from platforms.credit_govern.inference_rail import _parse_rail_response

    outcome = _parse_rail_response(
        {"predictions": [{"decision": "approve", "score": 0.77, "explanation_id": "sm-1"}]},
        provider="sagemaker",
        latency_ms=10,
    )
    assert outcome.decision == "APPROVE"
    assert outcome.score == 0.77
