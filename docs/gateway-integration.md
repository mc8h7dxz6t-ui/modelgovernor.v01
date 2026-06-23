# Gateway integration

The governance gateway (`gateway/app/main.py`) implements **reserve-before-dispatch**
semantics for governed LLM traffic.

## Flow

1. Client calls `POST /governed/dispatch` on the gateway.
2. Gateway calls sidecar `POST /reserve` with an internal token.
3. Gateway performs dispatch (mock or upstream provider in production overlays).
4. Gateway calls sidecar `POST /settle` with actual cost and provider request id.

## Environment

| Variable | Purpose |
|---|---|
| `SIDECAR_URL` | Sidecar base URL (default `http://sidecar:8081`) |
| `SIDECAR_INTERNAL_TOKEN` | Token for `x-internal-token` header |
| `MOCK_DISPATCH_COST` | Simulated actual cost for compose/demo |

## Local

```bash
docker compose up -d sidecar gateway
curl -X POST http://localhost:8080/governed/dispatch \
  -H 'content-type: application/json' \
  -d '{"user_id":"demo-user","trace_id":"t1","model":"gpt-4o-mini","estimated_cost":"5.000000"}'
```

## Kubernetes

Deployed via `deploy/base/gateway-deployment.yaml`. NetworkPolicy allows gateway → sidecar
ingress on port 8081.

LiteLLM configuration (`gateway/litellm.config.yaml`) remains available for provider
routing overlays; the governance gateway is the institutional reference integration.
