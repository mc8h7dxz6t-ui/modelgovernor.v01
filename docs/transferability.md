# Transferability and operational cleanliness

This repository is structured to reduce one-person or one-account operational coupling.

## Current portability posture

- Environment-driven configuration (`.env.example`; no hardcoded personal endpoints)
- Docker Compose-first local bring-up for evaluators
- PostgreSQL as explicit system of record for governance state
- Redis scoped to volatile runtime guardrails only
- SQL migrations in-repo and replayable in order

## Deliberate non-couplings

- No required personal cloud account
- No required personal DNS zone
- No required personal object bucket
- No required personal container registry
- No personal access tokens committed in scripts or docs

## Evaluator handoff checklist

1. Copy `.env.example` to `.env` and set internal values.
2. Run `make demo-up` and `make demo-smoke`.
3. Run proof checks (`docs/reliability-testing.md`).
4. Review ledger/event state via `make demo-ledger` and `make demo-events`.

## Repository hygiene expectations

- Do not commit `.env`, caches, `*.pyc`, or generated load artifacts.
- Keep claims tied to testable outputs and committed documentation.
