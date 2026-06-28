# Platform D — Enterprise Security Pack

**SKU:** `MG-ADDON-ENTERPRISE-SECURITY`  
**Tagline:** Zero-trust mesh, egress control, and live JWKS validation for regulated environments.

---

## Executive summary

Optional overlay for buyers with **InfoSec / zero-trust mandates**. Applies Istio `STRICT` mTLS, LLM provider egress allowlisting, and documents OIDC JWKS live validation in CI. Typically sold as add-on to **Platform C**, not standalone.

| | |
|---|---|
| **Target buyer** | CISO office, zero-trust architects, regulated industries (banking, health, gov) |
| **Sales motion** | Security review gate after technical win |
| **Time to live** | 2–4 weeks (Istio already on cluster) |
| **Maturity tier** | **L5 security overlay** — Istio STRICT + egress allowlist |

---

## Full technical specification

### What ships in-repo

```
deploy/overlays/enterprise/
├── kustomization.yaml
├── egress-istio.yaml          # ServiceEntry + AuthorizationPolicy
├── mtls-mesh.yaml             # PeerAuthentication STRICT
└── istio-injection-patches.yaml
```

### Network controls

| Resource | Purpose |
|---|---|
| `ServiceEntry` | Register `api.openai.com`, `api.anthropic.com` as mesh-external |
| `AuthorizationPolicy` | Gateway egress **only** to allowlisted hosts + in-cluster sidecar |
| `PeerAuthentication` | `STRICT` mTLS for modelgovernor namespace |
| Sidecar injection patches | Gateway + sidecar pods enrolled in mesh |

### Egress flow

```
Gateway pod ──mTLS──▶ Sidecar (in-cluster, allowlisted)
     │
     └──mTLS──▶ Istio egress gateway (optional) ──TLS──▶ api.openai.com
                                              └──TLS──▶ api.anthropic.com
```

Vertex AI: typically via GCP workload identity / private Google access — document in buyer-specific runbook.

### Identity integration (pairs with Platform C)

| Layer | Module | Behavior |
|---|---|---|
| Gateway edge | `gateway/app/auth_oidc.py` | JWT validation before dispatch |
| Sidecar admin | `sidecar/app/auth_oidc.py` | Viewer / Financial Admin on `/internal/*` |
| Live JWKS tests | `tests/integration/test_oidc_jwks_live.py` | Rotating-key fixture proves validation path |

### Configuration flags

| Variable | Production value |
|---|---|
| `GATEWAY_OIDC_ENABLED` | `true` |
| `OIDC_ENABLED` | `true` |
| `OIDC_ISSUER_URL` | Buyer IdP |
| `OIDC_JWKS_URL` | Buyer JWKS |
| `OIDC_DISPATCH_ROLES` | e.g. `ai-dispatch`, `financial-admin` |

### Deploy

```bash
# Requires Istio control plane installed
kubectl apply -k deploy/overlays/enterprise

# Production bundle already references enterprise overlay:
kubectl apply -k deploy/overlays/production
```

Helm: `enterprise.istio.enabled: true` in `values-production.yaml`.

### Security questionnaire answers (template)

| Question | Answer |
|---|---|
| Is traffic encrypted in transit? | Yes — Istio STRICT mTLS in-namespace |
| Can workloads exfiltrate to arbitrary hosts? | No — AuthorizationPolicy allowlist |
| How are admin APIs protected? | OIDC JWT + RBAC roles |
| How are secrets stored? | ExternalSecrets; no plaintext in Git |
| Audit trail for privileged actions? | `admin_audit` + hash-chained ledger |
| Tamper detection? | Hourly chain verify + S3 Object Lock anchor |

### Requirements

| Requirement | Notes |
|---|---|
| Istio 1.18+ | Control plane + ingress/egress gateways as designed |
| Corporate IdP | OIDC-compliant (Okta, Keycloak, Entra) |
| Platform C base | This is an overlay, not a standalone product |
| Pen test | Buyer responsibility; MG provides architecture pack |

### Proof artifacts

```bash
kustomize build deploy/overlays/enterprise | kubectl apply --dry-run=client -f -
pytest tests/integration/test_oidc_jwks_live.py -q
pytest tests/integration/test_auth_oidc.py -q
```

Docs: `docs/enterprise-hardening-roadmap.md`, `deploy/overlays/enterprise/README.md`

---

## Deployment packaging

### Bundle with Platform C

| Package | Components |
|---|---|
| Production Standard + Security | Platform C + Istio overlay |
| Production Premium + Security | C premium tier + Platform D |
| Production Strategic + Security | C strategic tier + full zero-trust pack |

---

## Maturity proof

| Component | Verified by |
|---|---|
| Istio manifests (egress + mTLS) | `deploy/overlays/enterprise/` |
| OIDC dual-layer implementation | Gateway + sidecar JWT (shared with C) |
| Live JWKS test harness | L4 CI JWKS probe |
| Security architecture docs | `docs/enterprise-hardening-roadmap.md` |

---

## Roadmap hooks (sales narrative)

- SOC 2 Type II attestation (organization — not repo alone)
- FIPS-compliant Redis / Postgres options
- Air-gapped Helm bundle for defense sector

Parent platform: [03-production-institutional.md](03-production-institutional.md)
