# Gateway integration

The governance gateway (`gateway/app/main.py`) implements **reserve-before-dispatch**
semantics for governed LLM traffic with live provider routing.

## Flow

1. Client calls `POST /governed/dispatch` (OIDC Bearer or internal token).
2. Gateway calls sidecar `POST /reserve` with an internal token.
3. Gateway routes to provider (`openai`, `anthropic`, `vertex`, or `mock`).
4. Gateway settles with **real token usage** mapped to ledger cost.

## Provider routing

| Model prefix | Provider | SDK |
|---|---|---|
| `gpt-*`, `openai/*` | OpenAI | `openai` |
| `claude-*`, `anthropic/*` | Anthropic | `anthropic` |
| `gemini-*`, `vertex/*` | Vertex AI | `google-cloud-aiplatform` |
| `PROVIDER_MODE=mock` | Mock | CI/dev |

Request body must include `prompt` or `messages` for live mode.

## Environment

| Variable | Purpose |
|---|---|
| `SIDECAR_URL` | Sidecar base URL |
| `SIDECAR_INTERNAL_TOKEN` | Token for sidecar reserve/settle |
| `PROVIDER_MODE` | `mock` (default) or `live` |
| `OPENAI_API_KEY` | OpenAI live routing |
| `ANTHROPIC_API_KEY` | Anthropic live routing |
| `VERTEX_PROJECT_ID` | Google Vertex project |
| `VERTEX_LOCATION` | Vertex region (default `us-central1`) |
| `GATEWAY_OIDC_ENABLED` | Require corporate JWT at gateway edge |

## Local (mock)

```bash
PROVIDER_MODE=mock docker compose up -d sidecar gateway
curl -X POST http://localhost:8080/governed/dispatch \
  -H 'content-type: application/json' \
  -H 'x-internal-token: dev-token' \
  -d '{"user_id":"demo-user","trace_id":"t1","model":"gpt-4o-mini","estimated_cost":"5.000000","prompt":"hello"}'
```

## Production

- `deploy/overlays/production` sets `PROVIDER_MODE=live`, OIDC, Redis Sentinel, ExternalSecrets
- Provider API keys sourced from secret manager via ExternalSecrets Operator
- S3 Object Lock bucket: `deploy/infra/aws/ledger-anchor-bucket.yaml`

## Kubernetes

Deployed via `deploy/base/gateway-deployment.yaml`. NetworkPolicy allows gateway → sidecar
ingress on port 8081. Enterprise overlay adds Istio egress allowlist for provider domains.
