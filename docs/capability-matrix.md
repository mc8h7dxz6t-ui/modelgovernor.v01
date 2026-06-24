# Capability matrix — institutional++ gold standard

Use this table in RFPs, security questionnaires, and enterprise diligence calls.

| Capability | Status | Demo | Production |
|---|---|---|---|
| Reserve-before-dispatch governance | ✅ | `make demo-gold` | Gateway + sidecar |
| Multi-provider routing (OpenAI, Anthropic, Vertex) | ✅ | Mock mode | `PROVIDER_MODE=live` |
| OpenAI-compatible API (`/v1/chat/completions`) | ✅ | Step 2 in `demo-gold` | `OPENAI_COMPAT_ENABLED` |
| Micro-cent token pricing (`NUMERIC(24,12)`) | ✅ | Auto | Migration `0008` |
| Append-only ledger + idempotent lifecycle | ✅ | Step 7 in `demo-gold` | Postgres |
| Per-trace atomic budget caps | ✅ | Auto | Sidecar |
| Drift enforcement + wallet lockout | ✅ | Step 10 in `demo-gold` | Sidecar |
| Leader-elected reconciler (expiry/stranded) | ✅ | Step 1 + 11 in `demo-gold` | 2+ replicas |
| Redis guardrails + local fallback | ✅ | Step 9 in `demo-gold` | Sidecar |
| Provider circuit breaker + local fallback | ✅ | Step 8 in `demo-gold` | Sidecar |
| Diagnostic mode (no poison pill) | ✅ | Step 5 in `demo-gold` | Redis cluster flag |
| Hash-chained ledger events | ✅ | Verify API | Migration `0009` |
| Hourly chain verification CronJob | ✅ | Documented | K8s CronJob |
| S3 Object Lock external anchor | ✅ | Documented | CloudFormation + ESO |
| Privileged admin audit log | ✅ | Step 11 in `demo-gold` | Migration `0010` |
| Gateway OIDC termination | ✅ | Documented | `GATEWAY_OIDC_ENABLED` |
| Sidecar OIDC + RBAC | ✅ | Documented | `OIDC_ENABLED` |
| ExternalSecrets (Vault / AWS SM / GCP) | ✅ | Documented | Production overlay |
| Redis Sentinel HA | ✅ | Documented | Production overlay |
| PgBouncer connection pooling | ✅ | HA compose | K8s + Helm |
| Istio egress allowlist + STRICT mTLS | ✅ | Documented | Enterprise overlay |
| Prometheus SLOs + burn-rate alerts | ✅ | `/metrics/prometheus` | PrometheusRule |
| Governance canary CronJobs | ✅ | Documented | K8s |
| GitOps (ArgoCD + Helm) | ✅ | Manifests in repo | `deploy/argocd` |
| 4-tier CI (unit → Postgres → load → chaos) | ✅ | `ci.yml` | GitHub Actions |

## Competitive positioning

- **vs. raw LiteLLM proxy:** ledger-backed settlement, not just request logging
- **vs. cloud-only budget alerts:** pre-dispatch enforcement, not post-hoc surprises
- **vs. homegrown wrappers:** institutional invariant test suite + reconciler HA

## Proof artifacts

```bash
make demo-gold              # live ~5-min walkthrough (11 steps)
make demo-gold-reliability  # steps 7–11 only (reliability drill)
pytest tests/integration/   # 57+ fast tests
pytest tests/chaos/         # Toxiproxy finance ops (Tier 4)
```
