# Sales demo — start here

**Plug-and-play institutional++ walkthrough. No API keys. No cloud. ~5 minutes.**

Covers governance, audit, diagnostic mode, and **live reliability drills** (idempotency, drift lockout, circuit breaker, Redis fallback).

### Prerequisites (bash)

```bash
make demo-prereqs-install   # Docker + Docker Compose + curl + make (Linux)
make demo-prereqs             # verify only
```

Or install manually: Docker Engine, [Compose plugin](https://docs.docker.com/compose/install/linux/), `curl`, `make`.

### Run the demo

```bash
make demo-gold-up
make demo-gold
```

**All platforms (A live + B/C/D manifest proof):**

```bash
make demo-all-platforms
```

See [docs/demo-all-platforms.md](docs/demo-all-platforms.md).

That's it. The script walks through every enterprise talking point live.

## What you get

- Governance gateway with multi-provider routing (mock)
- Postgres ledger with reserve/settle and audit trail
- Hash-chain verification + diagnostic mode drill
- **Institutional++ reliability:** idempotency replay, drift wallet lockout, provider circuit breaker, Redis guardrail fallback
- Reconciler leader election + privileged admin audit log
- Prometheus metrics and SLO surfaces
- Production flip chart (OIDC, Sentinel, S3, Istio) at the end

## Docs for the room

| Doc | Use |
|---|---|
| [docs/sales-demo.md](docs/sales-demo.md) | Talk track + troubleshooting |
| [docs/capability-matrix.md](docs/capability-matrix.md) | RFP / security questionnaire |
| [docs/plug-and-play.md](docs/plug-and-play.md) | Demo → staging → production |
| [docs/sales-sheets/](docs/sales-sheets/) | **Full spec + maturity tiers per platform** |
| [docs/institutional-reliability.md](docs/institutional-reliability.md) | Architecture deep dive |

## Teardown

```bash
make demo-gold-down
```
