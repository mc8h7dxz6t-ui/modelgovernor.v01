# Sales demo — start here

**Plug-and-play institutional++ walkthrough. No API keys. No cloud. ~5 minutes.**

```bash
make demo-gold-up
make demo-gold
```

That's it. The script walks through every enterprise talking point live.

## What you get

- Governance gateway with multi-provider routing (mock)
- Postgres ledger with reserve/settle and audit trail
- Hash-chain verification + diagnostic mode drill
- Prometheus metrics and SLO surfaces
- Production flip chart (OIDC, Sentinel, S3, Istio) at the end

## Docs for the room

| Doc | Use |
|---|---|
| [docs/sales-demo.md](docs/sales-demo.md) | Talk track + troubleshooting |
| [docs/capability-matrix.md](docs/capability-matrix.md) | RFP / security questionnaire |
| [docs/plug-and-play.md](docs/plug-and-play.md) | Demo → staging → production |
| [docs/sales-sheets/](docs/sales-sheets/) | **Full spec + pricing + pre-revenue valuation per platform** |
| [docs/institutional-reliability.md](docs/institutional-reliability.md) | Architecture deep dive |

## Teardown

```bash
make demo-gold-down
```
