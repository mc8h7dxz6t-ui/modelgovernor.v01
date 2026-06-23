# Enterprise overlay

Optional Istio egress allowlist for LLM provider domains. Apply on clusters with Istio installed:

```bash
kubectl apply -k deploy/overlays/enterprise
```

Includes base workload manifests plus:
- `ServiceEntry` for `api.openai.com` and `api.anthropic.com`
- `AuthorizationPolicy` restricting gateway egress to allowlisted hosts + in-cluster sidecar

See `docs/enterprise-hardening-roadmap.md` for full zero-trust rollout.
