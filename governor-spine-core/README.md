# Governor Spine Core

Authoritative **port map** and **ledger table registry** for all four governors. This package does not replace per-governor SQLAlchemy sidecars — it provides the consolidation contract and repository integrity checks.

## Maturity label

Use **Institutional Self-Check Certified** for pytest + helm-render + port-alignment gates. Do not claim third-party L5 or "Industry Leading" without external audit.

## Verify

```bash
PYTHONPATH=governor-spine-core python3 -m pytest governor-spine-core/tests/ -q
make plug   # full portfolio salvage verification
```

## Port map

| Governor | Gateway | Sidecar | Reconciler |
|----------|---------|---------|------------|
| ModelGovernor | 8080 | 8081 | 8082 |
| Finance | 8090 | 8091 | 8092 |
| Insurance | 8100 | 8101 | 8102 |
| Cybersecurity | 8120 | 8121 | 8122 |

Dockerfile `--port` must match compose `host:container` publish ports (FG/IG/CG enforced by `port_checks.py`).
