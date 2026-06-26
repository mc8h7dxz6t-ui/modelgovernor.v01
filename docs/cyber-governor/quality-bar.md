# Quality bar — merge gate

Cybersecurity Governor PRs must pass:

1. `make cg-spine-test` — all unit tests green
2. No regression on hash chain verify after mutations
3. New invariant behavior includes probe + counter
4. K8s manifest changes render with `kustomize build deploy/base/`
5. Docs updated for new platform APIs or env vars

## Platform checklist (each wedge)

- [ ] Standalone mode (`CG_SPINE_ENABLED=false`)
- [ ] Spine adapter integration when enabled
- [ ] Health endpoint `/healthz`
- [ ] Tier 1 tests
- [ ] Listed in `capability-matrix.md`
