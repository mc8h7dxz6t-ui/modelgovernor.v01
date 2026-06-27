import hashlib
from decimal import Decimal

from platforms.parametric_oracle.trigger_gate import evaluate_trigger, verify_oracle_attestation


def _attest(source: str, payload: str) -> str:
    return hashlib.sha256(f"{source}:{payload}".encode()).hexdigest()


def test_trigger_fires_above_threshold():
    result = evaluate_trigger(
        event_id="evt-1",
        metric_value=Decimal("7.2"),
        threshold=Decimal("6.5"),
        oracle_verified=True,
    )
    assert result.triggered is True
    assert result.decision == "TRIGGERED"


def test_below_threshold_not_triggered():
    result = evaluate_trigger(
        event_id="evt-2",
        metric_value=Decimal("4.0"),
        threshold=Decimal("6.5"),
        oracle_verified=True,
    )
    assert result.triggered is False
    assert result.decision == "BELOW_THRESHOLD"


def test_oracle_attestation_verification():
    payload = '{"magnitude":7.2}'
    h = _attest("usgs-feed", payload)
    assert verify_oracle_attestation(source="usgs-feed", payload=payload, attestation_hash=h)


def test_parametric_standalone_spine_adapter():
    from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

    adapter = SpineAdapter(platform="parametric_oracle", spine_enabled=False)
    facets = {"event_id": "local-trig-1", "metric_value": "7.0", "threshold": "6.5"}
    crystal = adapter.crystallize("local-trig-1", "critical", facets)
    adapter.commit(
        CommitOutcome(
            operation_id="local-trig-1",
            crystal_id=crystal.crystal_id,
            facets=facets,
            outcome="triggered",
            committed_reserve="10000.00",
        )
    )
