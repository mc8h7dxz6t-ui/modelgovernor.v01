# Governor Spine Core

Authoritative **port map**, **ledger table registry**, and **repository integrity checks** for all four governors.

This package is the consolidation **contract** — not a replacement for per-governor SQLAlchemy sidecars.

## Maturity labels

| Label | Proof | Use when |
|-------|-------|----------|
| **L4 Gold Enterprise** | Per-governor 4-tier CI + Helm | Sale-ready engineering baseline |
| **L5 Institutional Self-Check** | `make plug` | Portfolio offline harness |
| **Industry Leading Gold Standard** | L4+L5 + live attestation + external evidence | Acquirer / design-partner diligence only |

**Industry Leading** describes **kernel architecture class** (crystallize → seal → commit → prove), not broad-market SaaS readiness. See [docs/maturity-ladder.md](docs/maturity-ladder.md) and [docs/transactional-kernel-strategy.md](docs/transactional-kernel-strategy.md).

## Modules

| Module | Purpose |
|--------|---------|
| `config.py` | `GovernorDomain`, ports 808x–812x, ledger table names |
| `port_checks.py` | Spine Dockerfile/compose alignment + platform port drift |
| `mode_contract.py` | Maps Active/Mock to existing env vars (no new singleton) |
| `verify_http.py` | HTTP client for sidecar `verify-chain` endpoints |
| `docs/transactional-kernel-strategy.md` | Tech edge, commercial headwinds, buyer fit |
| `docs/maturity-ladder.md` | L4 / L5 / Industry Leading definitions |
| `docs/disaster-recovery-runbook.md` | Honest DR — circuit breaker, diagnostic, fallback |

## Verify

```bash
make plug                              # full portfolio harness
python -m spine_core.port_checks       # ports only
PYTHONPATH=governor-spine-core pytest governor-spine-core/tests/ -q
make compose-smoke-cg                  # optional live CG (Docker)
```

## What we deliberately did NOT add

- Parallel `psycopg2` ledger writer (duplicates existing `commit_ledger.py` in each governor)
- Kubernetes CronJob that `kubectl patch`es deployments on `curl openai.com` failure
- Global singleton "mode controller" — use existing guardrails + diagnostic mode

Chain cryptography stays in each governor's `*_seal.py`; verify via HTTP `verify-chain`.
