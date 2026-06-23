# Service level objectives (institutional++)

## Reserve availability

| Field | Value |
|---|---|
| SLI | Ratio of `/reserve` HTTP responses with status 2xx to all `/reserve` requests |
| Target | **99.5%** over rolling 30 days |
| Measurement window | 5-minute rate (`modelgovernor:reserve_success_rate:5m`) |
| Alert | `ModelGovernorReserveAvailabilitySLO` when below 0.995 for 10 minutes |

## Reserve latency

| Field | Value |
|---|---|
| SLI | p95 latency of `/reserve` handler (`modelgovernor_http_request_duration_seconds`) |
| Target | **≤ 500ms** p95 under nominal load |
| Measurement window | 5-minute histogram quantile |
| Alert | `ModelGovernorReserveLatencySLO` when p95 > 0.5s for 10 minutes |

## Financial safety invariants (error budget = zero)

These invariants have **no error budget**. Any increase triggers immediate critical response:

| Invariant | Counter / signal |
|---|---|
| Negative wallet | `negative_wallet_detected_total` |
| Duplicate refund | `duplicate_refund_anomaly_total` |
| Duplicate settlement | `duplicate_settlement_anomaly_total` |
| Post-sweep audit failure | `finance_audit_violation_total` |

## Operational guardrails

| Signal | Target | Notes |
|---|---|---|
| Redis guardrail degradation | < 1% of reserves in 15m window | `guardrail_degraded_total` — ledger remains correct |
| Balance-denied reserves | Baseline + spike alert | `reserve_denied_balance_total` |
| Drift lockouts | Baseline + spike alert | `drift_enforced_total` |

## Scrape surfaces

- **PodMonitor / Prometheus**: `GET /metrics/prometheus` (unauthenticated process + RED metrics)
- **Operator deep dive**: `GET /metrics` with internal token (DB aggregates + invariant counters)
