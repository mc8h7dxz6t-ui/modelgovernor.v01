# Shadow / enforce mode — zero-brick guarantee

## SRE answer

> Deploy in **SHADOW** first: full evaluation, structured metrics, **never block** production on internal errors or policy failures. Flip to **ENFORCE** only after SLO and policy sign-off.

## Semantics

| Mode | Validation passes | Validation fails | Evaluator timeout/crash |
|------|-------------------|------------------|-------------------------|
| **SHADOW** | ALLOW | ALLOW + warning metric | ALLOW + error metric |
| **ENFORCE** | ALLOW | DENY | DENY (fail closed on authorize) |

This is **not** fail-open on ENFORCE — only SHADOW guarantees passthrough.

## Configuration

| Env | Default | Description |
|-----|---------|-------------|
| `ENFORCEMENT_MODE` | `SHADOW` | `SHADOW` or `ENFORCE` |
| `ENFORCEMENT_LATENCY_SLO_MS` | `50` | Warning threshold |
| `ENFORCEMENT_EVALUATOR_TIMEOUT_MS` | `45` | Hard cap on evaluator (thread pool) |

## Implementation

`sidecar/app/enforcement_mode.py` — `execute_intercept_gate()`

- Evaluator runs in bounded thread pool with timeout (prevents hung request blocking forever in ENFORCE).
- Metrics: `governor_intercept_*` counters via `metrics.json`.

## Pilot rollout (gold standard)

1. **Week 1–2:** SHADOW on all commit paths — collect `shadow_passthrough` rate.
2. **Week 3:** Review false-positive rate with buyer security + SRE.
3. **Week 4+:** ENFORCE on **one** path (e.g. egress only) with rollback flag.

## Latency

Shadow evaluation still consumes time. Target p95 < 50ms on reference hardware. If SLO breached:

- Reduce evaluator work
- Move heavy checks async **only for SHADOW metric emission** (core path stays sync with timeout)

**Do not** claim zero latency tax — claim **bounded tax + SHADOW never bricks**.

## Tests

```bash
PYTHONPATH=. pytest tests/integration/test_enforcement_mode.py -q
```

## Related

- [TENANT-RLS.md](TENANT-RLS.md)
- [../ROADMAP-COMMERCIAL-9.md](../ROADMAP-COMMERCIAL-9.md)
