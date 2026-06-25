from decimal import Decimal

from platforms.claim_gate.payout_gate import evaluate_payout


def test_auto_approve_within_limit():
    result = evaluate_payout(
        claim_id="c1",
        payout_amount=Decimal("10000.00"),
        policy_limit=Decimal("5000000.00"),
        auto_approve_limit=Decimal("250000.00"),
    )
    assert result.approved is True
    assert result.decision == "APPROVED"


def test_held_above_auto_approve():
    result = evaluate_payout(
        claim_id="c2",
        payout_amount=Decimal("400000.00"),
        policy_limit=Decimal("5000000.00"),
        auto_approve_limit=Decimal("250000.00"),
    )
    assert result.approved is False
    assert result.decision == "HELD"


def test_referred_on_siu():
    result = evaluate_payout(
        claim_id="c3",
        payout_amount=Decimal("1000.00"),
        policy_limit=Decimal("5000000.00"),
        auto_approve_limit=Decimal("250000.00"),
        siu_flag=True,
    )
    assert result.decision == "REFERRED"


def test_standalone_spine_adapter_local_mode():
    from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

    adapter = SpineAdapter(platform="claim_gate", spine_enabled=False)
    facets = {"claim_id": "local-1", "payout_amount": "100.00"}
    crystal = adapter.crystallize("local-1", "high", facets)
    adapter.commit(
        CommitOutcome(
            operation_id="local-1",
            crystal_id=crystal.crystal_id,
            facets=facets,
            outcome="paid",
            committed_reserve="100.00",
        )
    )
