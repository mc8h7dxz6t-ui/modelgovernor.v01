# All platforms — collated demo playbook

One scripted path for **Platform A (live)** + **Platforms B/C/D (manifest proof)** + optional engineering proof. Use in investor calls, enterprise diligence, and partner enablement when you need the full SKU story in one sitting.

## Quick start

```bash
# Full collated demo (~6 min): live Platform A + render B/C/D manifests
make demo-all-platforms

# Live sales walkthrough only (Platform A)
make demo-all-platforms-live

# Manifest / GitOps proof only (no Docker) — good for K8s-native buyers
make demo-all-platforms-manifests

# Add Postgres invariant proof tests after live demo
make demo-all-platforms-proof
```

## What runs

| Platform | SKU | What this demo shows | How |
|----------|-----|----------------------|-----|
| **A — Sales Demo** | `MG-PLATFORM-DEMO` | Reserve-before-dispatch, multi-provider mock, diagnostic mode, institutional++ reliability | **Live** — `make demo-gold` (11 steps) |
| **B — Staging / Pilot** | `MG-PLATFORM-STAGING` | Customer VPC pilot, live providers, 2+ sidecar replicas, HPA | **Manifest** — `kustomize build deploy/overlays/staging` |
| **C — Production** | `MG-PLATFORM-PRODUCTION` | Sentinel, OIDC, S3 anchor, CronJobs, PgBouncer | **Manifest** — `kustomize build deploy/overlays/production` |
| **D — Enterprise Security** | `MG-ADDON-ENTERPRISE-SECURITY` | Istio STRICT mTLS, LLM egress allowlist | **Manifest** — `kustomize build deploy/overlays/enterprise` |

Platform **C includes D** in the production overlay. Platform **A** is the only layer that runs fully offline on a laptop with Docker.

## 15-minute room script

1. **2 min — Platform matrix** (printed at start of `make demo-all-platforms`)
2. **3 min — B/C/D manifest proof** (shows rendered K8s objects, OIDC/Sentinel/Istio knobs)
3. **5 min — Platform A live** (`make demo-gold` — governance + reliability)
4. **2 min — Flip chart** (demo closing table + `docs/plug-and-play.md`)
5. **Optional 3 min — `make proof-test`** for engineering buyers

## Prerequisites

| Requirement | Platform A | B/C/D manifests |
|-------------|------------|-----------------|
| Docker + Compose | Required | — |
| `kustomize` | — | Optional (skipped with install hint) |
| `helm` | — | Optional (template summary) |
| Kubernetes cluster | — | Not required for manifest render |

Mac: install [kustomize](https://kubectl.docs.kubernetes.io/installation/kustomize/) and [helm](https://helm.sh/docs/intro/install/) for full B/C/D output.

## Commands reference

```bash
make demo-gold-up              # start Platform A stack (auto-run if down)
make demo-gold                 # Platform A only (11 steps)
make demo-gold-reset           # before rerun (wallet locked after drift drill)
make demo-gold-down            # teardown

make demo-all-platforms        # A live + B/C/D manifests
make demo-all-platforms-live   # A only
make demo-all-platforms-manifests
make demo-all-platforms-proof  # collated + proof-test
```

## Deep specs per platform

| Sheet | Path |
|-------|------|
| Platform A | [docs/sales-sheets/01-demo-platform.md](sales-sheets/01-demo-platform.md) |
| Platform B | [docs/sales-sheets/02-staging-pilot-platform.md](sales-sheets/02-staging-pilot-platform.md) |
| Platform C | [docs/sales-sheets/03-production-institutional.md](sales-sheets/03-production-institutional.md) |
| Platform D | [docs/sales-sheets/04-enterprise-security-pack.md](sales-sheets/04-enterprise-security-pack.md) |

Also: [capability-matrix.md](capability-matrix.md) · [plug-and-play.md](plug-and-play.md) · [SALES-DEMO.md](../SALES-DEMO.md)

## Troubleshooting

- **Platform A 409 errors:** `make demo-gold-reset` then `make demo-gold-diagnose`
- **Wallet locked after demo:** expected (step 10 drift drill) — `make demo-gold-reset`
- **kustomize not found:** install kustomize or rely on CI-green `main` branch manifests
- **Do not paste `# comments` on same line as make** — zsh/make will treat `#` as a target
