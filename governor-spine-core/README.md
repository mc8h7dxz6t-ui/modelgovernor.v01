# Governor Spine Core

Authoritative **port map**, **ledger table registry**, and **repository integrity checks** for all four governors.

This package is the consolidation **contract** — not a replacement for per-governor SQLAlchemy sidecars.

## Portfolio readiness (implementation-based)

| Layer | Score |
|-------|-------|
| Core transactional kernel | **8.5/10** |
| ModelGovernor | **7.0/10** |
| FG / CG / IG wedges | **6.0/10** |
| **Combined portfolio** | **6.5/10** |

Full scorecard: [docs/operational-architecture-scorecard.md](docs/operational-architecture-scorecard.md)

## Maturity labels

| Label | Proof |
|-------|-------|
| **L4 Gold Enterprise** | Per-governor 4-tier CI + Helm |
| **L5 Institutional Self-Check Certified** | `make plug` — CI job `portfolio-plug` (not SOC2 / ISO) |
| **Industry Leading (kernel)** | L4+L5 + live attestation + external evidence — see [maturity-ladder.md](docs/maturity-ladder.md) |

## Docs

| Doc | Purpose |
|-----|---------|
| [operational-architecture-scorecard.md](docs/operational-architecture-scorecard.md) | **6.5/10** portfolio score + exit paths |
| [forensic-audit-evidence.md](docs/forensic-audit-evidence.md) | Acquirer due diligence — provable engine vs gaps |
| [transactional-kernel-strategy.md](docs/transactional-kernel-strategy.md) | Tech edge + buyer fit |
| [maturity-ladder.md](docs/maturity-ladder.md) | L4 / L5 / IL definitions |
| [disaster-recovery-runbook.md](docs/disaster-recovery-runbook.md) | Honest DR patterns |

## Verify

```bash
make plug
python -m spine_core.port_checks
make compose-smoke-cg    # optional live CG
```

## What we deliberately did NOT add

- Parallel `psycopg2` ledger writer
- Kubernetes CronJob that `kubectl patch`es on `curl openai.com`
- Global singleton mode controller

Chain cryptography stays in each governor's `*_seal.py`; verify via HTTP `verify-chain`.
