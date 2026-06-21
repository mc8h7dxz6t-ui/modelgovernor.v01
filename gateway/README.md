# Gateway scaffold

This directory provides a minimal LiteLLM gateway baseline for provider-agnostic routing.

## Important governance boundary

All governed inference traffic must pass through sidecar controls for reserve-before-dispatch and settlement lifecycle enforcement.
The gateway should not bypass sidecar policy checks for production-governed routes.

## Environment placeholders

Set provider credentials and gateway key via environment variables:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `LITELLM_MASTER_KEY`
- `SIDECAR_BASE_URL`

Use `litellm.config.yaml` as the routing shape baseline and adjust models/providers per deployment.
