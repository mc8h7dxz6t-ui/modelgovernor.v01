"""Bias cohort monitoring tests."""
from decimal import Decimal

from platforms.common.bias_monitoring import record_credit_cohort
from platforms.common.platform_metrics import get_platform_counters


def test_bias_alert_on_low_score_approve():
    counters = get_platform_counters("credit_govern_test")
    before = counters.snapshot().get("bias_cohort_alert_total", 0)
    record_credit_cohort(
        platform="credit_govern_test",
        desk_id="desk-1",
        model_version_id="v3",
        application_id="app-1",
        score=0.3,
        decision="APPROVE",
        exposure=Decimal("1000"),
    )
    after = counters.snapshot().get("bias_cohort_alert_total", 0)
    assert after == before + 1
