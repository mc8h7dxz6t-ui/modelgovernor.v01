# AlgoFreeze — Dynamic Network Freeze for Live Algo Systems

**Standalone platform** preventing runaway algorithmic trading from bad deploys, feed degradation, or version drift.

## Problem

Knight Capital (2012): ~$440M lost in ~45 minutes from unintended code activation. Algos require split-second integrity across feeds, latency, and deployed version.

## Solution

Heartbeat proxy in front of order egress:

- **Version guard** — runtime SHA must match `approved_version_registry`
- **Feed heartbeat** — async monitor; missed packets trigger degrade → freeze
- **Circuit breaker** — block all order egress in `FROZEN` state
- **Append-only freeze events** — tamper-evident audit

## Deployment modes

| Mode | Command (target) | Dependencies |
|------|------------------|--------------|
| Standalone | `make algofreeze-demo` | Proxy + Redis + Postgres |
| Spine-connected | `FG_SPINE_ENABLED=true` | + Finance Governor sidecar |

## Standalone architecture

```
Feeds (Bloomberg, etc.) ──► AlgoFreeze Proxy ──► EMS / Exchange
                                 │
                    version_guard + feed_heartbeat
                    freeze_controller + order_gate
                                 │
                            platform_events (Postgres)
```

## Spine integration (optional)

- `reserve` notional per order batch
- Freeze → `strand` in-flight batches
- Cross-platform: WireMatch can block wires if desk is FROZEN

## Core invariants

| Invariant | Enforcement |
|-----------|-------------|
| No orders in FROZEN | `order_gate.py` hard block |
| Version mismatch → freeze | `version_guard.py` |
| Freeze events append-only | Postgres + optional hash chain |
| Feed gap within policy | `feed_heartbeat.py` |

## Module map

| File | Purpose |
|------|---------|
| `version_guard.py` | Deployed vs approved version |
| `feed_heartbeat.py` | Async packet cadence monitor |
| `freeze_controller.py` | ACTIVE → DEGRADED → FROZEN |
| `order_gate.py` | Egress allow/deny |
| `platform_events.py` | Local audit (standalone) or spine adapter |

## Tests (target)

```bash
pytest -q tests/programs/algofreeze/
# test_version_mismatch_freezes.py
# test_feed_gap_freezes.py
# test_no_egress_when_frozen.py
# test_standalone_without_spine.py
# test_spine_connected_reserve_strand.py
```

## ModelGovernor ports

- `circuit_breaker.py` → feed + rail breaker
- `diagnostic_mode.py` → freeze persistence
- `finance_ops.py` → post-sweep invariant probes
