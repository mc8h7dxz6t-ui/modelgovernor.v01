from decimal import Decimal

from platforms.bind_authority.bind_gate import evaluate_bind


def test_auto_bind_within_premium_band():
    result = evaluate_bind(
        application_id="app-1",
        premium=Decimal("25000.00"),
        limit=Decimal("1000000.00"),
        auto_bind_premium=Decimal("50000.00"),
    )
    assert result.approved is True
    assert result.decision == "BOUND"


def test_held_above_auto_bind_premium():
    result = evaluate_bind(
        application_id="app-2",
        premium=Decimal("75000.00"),
        limit=Decimal("1000000.00"),
        auto_bind_premium=Decimal("50000.00"),
    )
    assert result.approved is False
    assert result.decision == "HELD"


def test_declined_on_sanctions():
    result = evaluate_bind(
        application_id="app-3",
        premium=Decimal("1000.00"),
        limit=Decimal("100000.00"),
        auto_bind_premium=Decimal("50000.00"),
        sanctions_flag=True,
    )
    assert result.decision == "DECLINED"


def test_bind_standalone_spine_adapter():
    from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

    adapter = SpineAdapter(platform="bind_authority", spine_enabled=False)
    facets = {"application_id": "local-bind-1", "premium": "1000.00", "limit": "50000.00"}
    crystal = adapter.crystallize("local-bind-1", "high", facets)
    adapter.commit(
        CommitOutcome(
            operation_id="local-bind-1",
            crystal_id=crystal.crystal_id,
            facets=facets,
            outcome="bound",
            committed_reserve="1000.00",
        )
    )
