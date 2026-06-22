# Gateway

This directory provides the LiteLLM gateway baseline for provider-agnostic routing.

## Governance boundary

All governed inference traffic must pass through the policy sidecar. The gateway enforces the reserve-before-dispatch contract:

1. **Before dispatch** — call `POST /reserve` on the policy sidecar with the request metadata and `idempotency_key`. Include `X-Internal-Token` using the value of `GATEWAY_TO_SIDECAR_TOKEN`. If the sidecar returns a non-200 response, reject the request without dispatching upstream.
2. **After provider response** — call `POST /settle` with the `idempotency_key`, `actual_cost` derived from the provider usage response, and the `provider_request_id` captured from the provider response headers. Include `X-Internal-Token` with the same token.

The gateway must never dispatch to a provider without a committed reservation in the sidecar ledger.

## Trust boundary

- The gateway authenticates inbound client requests via `LITELLM_MASTER_KEY`.
- The gateway authenticates outbound sidecar calls via `GATEWAY_TO_SIDECAR_TOKEN`, which must match one of the tokens in the sidecar's `SIDECAR_INTERNAL_TOKENS` list.
- These are separate credentials with separate scopes. Rotate them independently.

## Environment variables

| Variable | Purpose |
|---|---|
| `LITELLM_MASTER_KEY` | Client-facing gateway master key |
| `GATEWAY_TO_SIDECAR_TOKEN` | Internal token for gateway→sidecar calls |
| `OPENAI_API_KEY` | OpenAI provider credential |

Use `litellm.config.yaml` as the routing baseline. Adjust models and providers per deployment.
