# Sales demo — institutional++ walkthrough

**Zero setup for prospects.** No API keys, cloud accounts, Istio, or IdP required.

```bash
make demo-gold-up    # ~2 min first build
make demo-gold       # ~5 min live walkthrough (11 steps)
make demo-gold-down
```

Optional: run reliability steps 7–11 only (stack must already be up):

```bash
make demo-gold-reliability
```

## What the buyer sees

| Step | Story | Endpoint |
|---|---|---|
| 1 | Full HA control plane + reconciler leader election | `/readyz` on gateway, sidecar, reconciler |
| 2 | Governed dispatch (reserve → provider → settle) | `POST /governed/dispatch` |
| 3 | Multi-provider routing (OpenAI, Anthropic, Vertex) | Same gateway, mock mode |
| 4 | Tamper-evident ledger hash chain | `GET /internal/ledger/verify-chain` |
| 5 | Diagnostic mode — incident without outage | Reserve 503 → operator clear |
| 6 | SLO metrics + invariant counters | `/metrics/prometheus` |
| 7 | Idempotency replay — no double-spend | `POST /reserve` replay |
| 8 | Provider circuit breaker — storm protection | Open circuit → reserve 409 |
| 9 | Redis guardrail degradation — local fallback | Stop Redis → reserve still bounded |
| 10 | Drift enforcement — wallet lockout | Over-settle → 409 on next reserve |
| 11 | Admin audit log + ledger trail + reconciler leader | `/internal/admin/audit/recent` |

## Talk track (60 seconds)

> "Every LLM call flows through a **governance gateway** that reserves budget before dispatch — like a pre-auth hold on a credit card. We route to OpenAI, Anthropic, or Vertex, then settle against **real token usage** on an append-only Postgres ledger with **micro-cent precision**.
>
> If finance invariants break, we enter **diagnostic mode** — automated sweeps halt, but your operators keep full read access to fix data. No poison-pill outage.
>
> The ledger is **hash-chained** for tamper evidence, verified hourly, and anchored to **S3 Object Lock** in production.
>
> Under the hood: **idempotent lifecycle**, drift lockout, Redis guardrails with graceful degradation, provider circuit breakers, leader-elected reconciler, 99.5% reserve SLO, and GitOps to Kubernetes with optional Istio mTLS."

## Flip to production (one slide)

| Demo (now) | Production (config flip) |
|---|---|
| `PROVIDER_MODE=mock` | `live` + provider API keys via ExternalSecrets |
| Internal token | OIDC / Keycloak / Okta |
| Single Redis | Redis Sentinel or ElastiCache |
| `docker compose` | `deploy/overlays/production` or Helm |

See `docs/plug-and-play.md` and `docs/capability-matrix.md`.

## Troubleshooting

- **Port conflict:** stop local Postgres/Redis on 5432/6379 or change compose ports.
- **Build slow:** first `demo-gold-up` builds images; subsequent runs are fast.
- **HTTP 409 on step 2:** pull latest `cursor/fix-demo-gold-409-6b52` or `main` — approval threshold and state reset fixes.
- **Wallet locked after demo:** expected after step 10 (drift drill). Run `make demo-gold-reset` before the next walkthrough.
- **Reset:** `make demo-gold-reset` or `make demo-gold-down` (`down -v` clears Postgres volume).
