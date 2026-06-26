# PostureReconcile — Platform Spec (1 page)

**SKU:** `CG-POSTURERECONCILE`  
**Port:** `8107`  
**Entry API:** `POST /posture/evaluate`

## Problem

CNAPP and posture scanners (Wiz, Prisma, K8s admission) emit **alerts after drift**. Authorize-time decisions still rely on stale baselines. **PostureReconcile** closes the gap by crystallizing **live posture vs approved baseline** before workload authorize or deploy commit.

## Scope (narrow — not a CNAPP replacement)

| In scope | Out of scope |
|----------|--------------|
| TCP gate at authorize/deploy time | Full cloud asset inventory UI |
| Compare live scan facets to approved crystal | Agentless scanning engine |
| STRAND on critical drift | Remediation orchestration (partner SOW) |
| Threat Mesh parent for egress/content wedges | Replacing LineageIngest structural DAG |

## API

### `POST /posture/evaluate`

**Request**

| Field | Type | Description |
|-------|------|-------------|
| `evaluation_id` | string | Idempotent operation id |
| `resource_id` | string | Workload / account / cluster id |
| `source` | string | `wiz`, `prisma`, `k8s`, `generic` |
| `posture_score` | int 0–100 | Live score from scanner |
| `failed_controls` | string[] | Control ids failing (e.g. `public_s3_bucket`) |
| `approved_baseline_id` | string | Registered baseline crystal reference |

**Response**

| Field | Values |
|-------|--------|
| `decision` | `ALLOWED`, `REMEDIATE`, `STRANDED` |
| `posture_state` | `COMPLIANT`, `DRIFT`, `STRANDED` |
| `drift_score` | float 0–1 |
| `reason` | string \| null |
| `crystal_id` | string \| null (when spine enabled) |

### Demo baseline (default)

- `min_posture_score`: **80**
- `critical_controls`: `public_s3_bucket`, `admin_port_open`, `unencrypted_volume`
- Score &lt; 80 or any critical control → **STRANDED**
- Other failed controls → **REMEDIATE**
- Clean scan → **ALLOWED**

## TCP / spine integration

- Platform id: `posture_reconcile`
- Risk tier: `high`
- Policy id: `posture-high-us`
- Facets sealed: `resource_id`, `source`, `posture_score`, `failed_controls`, `posture_state`, `drift_score`
- **Commit** only when `decision == ALLOWED`

## Threat Mesh

| Parent | Facet | Value | Blocks child |
|--------|-------|-------|--------------|
| `posture_reconcile` | `posture_state` | `STRANDED` | `egress_lock`, `content_guard` |

## Deployment

```bash
CG_SPINE_ENABLED=false make posture-reconcile-demo   # standalone
docker compose up -d cg-posture-reconcile            # with spine
```

## Tests

- Unit: compliant allow, critical drift strand, minor drift remediate
- Integration: health + core API in `test_platforms_smoke`
- Mesh: STRANDED posture blocks egress commit (optional spine test)

## Competitive edge

**vs Wiz/Prisma alone:** deterministic **crystallize-before-authorize** with hash-chained proof, not dashboard alert volume.
