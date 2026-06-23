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
| **Suggested ACV add-on (list)** | **+$80K–$200K / year** |
| **Pre-revenue asset worth** | **$350K–$650K** |

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

## Commercial packaging

### Add-on pricing (pre-revenue list)

| Component | Annual add-on |
|---|---|
| Enterprise overlay license | +$50K–$100K |
| Istio integration PS | $25K–$50K one-time |
| IdP hardening workshop | $15K–$25K one-time |
| **Typical bundle** | **+$80K–$200K / yr** |

### Bundle with Platform C

| Package | Combined ACV |
|---|---|
| Production Standard + Security | $430K–$650K |
| Production Premium + Security | $580K–$850K |
| Production Strategic + Security | $780K–$1.1M+ |

---

## Pre-revenue worth

| Component | Estimate |
|---|---|
| Istio manifests (egress + mTLS) | $80K–$150K |
| OIDC dual-layer implementation | $120K–$220K (shared with C — partial) |
| Live JWKS test harness | $40K–$80K |
| Security architecture docs | $30K–$60K |
| **Incremental asset worth (add-on slice)** | **$350K–$650K** |

---

## Roadmap hooks (sales narrative)

- SOC 2 Type II attestation (not yet — increases valuation +$1M–$2M when complete)
- FIPS-compliant Redis / Postgres options
- Air-gapped Helm bundle for defense sector

Parent platform: [03-production-institutional.md](03-production-institutional.md)
