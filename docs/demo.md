# Local demo (Docker Compose first)

This demo path is for evaluator walkthroughs, not performance claims.
This is the repository's **standalone/local evaluation mode**: sidecar + reconciler + Postgres + Redis (no gateway container in this Compose runtime).

## Prerequisites

- Docker + Docker Compose plugin
- `curl`
- `make`

## Startup (about 2-5 minutes on first run)

```bash
make demo-up
```

`make demo-up`:
- starts Postgres, Redis, sidecar, reconciler
- ensures `.env` exists (copied from `.env.example` if needed)
- applies `migrations/0001` through `migrations/0004`

## Happy-path governed request demo

```bash
make demo-smoke
```

This runs reserve + settle for `demo-user`, then prints:
- wallet state
- escrow ledger row
- operation event sequence

## Drift-lock / denial demo

```bash
make demo-drift-lock
```

This intentionally settles above reserve to trigger drift enforcement, then attempts a new reserve and confirms deterministic denial (HTTP 409) for the locked wallet.

## Inspect state

```bash
make demo-status
make demo-ledger
make demo-events
```

`make demo-status` now also calls the sidecar's internal-auth read and metrics surfaces:
- `/internal/wallet/demo-user`
- `/internal/events/recent`
- `/metrics`

This gives an API-first diligence path in addition to direct SQL views.

## Tear down

```bash
make demo-down
```

To reset DB volume and restart clean:

```bash
make demo-reset
```

## Troubleshooting

- If the sidecar is not ready yet, rerun `make demo-smoke` after `make demo-status`.
- If migration errors appear, run `make demo-reset` and then `make demo-up`.
- If a port is in use, stop conflicting local services on `5432`, `6379`, `8081`, or `8082`.
