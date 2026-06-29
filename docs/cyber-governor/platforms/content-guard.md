# ContentGuard — Platform Spec (1 page)

**SKU:** `CG-CONTENTGUARD`  
**Port:** `8108`  
**Entry API:** `POST /content/evaluate`

## Problem

DLP and content filters often run **after** publish or at network edge only. **ContentGuard** governs **sensitive content before publish/commit** — PII, secrets, regulated tokens — with TCP crystals bound to channel and classification.

## Scope (narrow — not full Zscaler DLP)

| In scope | Out of scope |
|----------|--------------|
| Pre-publish / pre-API content gate | Full ML classification suite |
| Pattern-based PII/secret detect + redact | Image/video DLP |
| HELD/BLOCKED/ALLOW with crystal | Enterprise data catalog |
| Threat Mesh child of posture + parent of egress | Replacing EgressLock byte policy |

## API

### `POST /content/evaluate`

**Request**

| Field | Type | Description |
|-------|------|-------------|
| `content_id` | string | Idempotent operation id |
| `principal_id` | string | Actor publishing content |
| `channel` | string | `publish`, `email`, `api`, `chat` |
| `text_body` | string | Content to evaluate |
| `classification_hint` | string | `public`, `internal`, `confidential`, `restricted` |

**Response**

| Field | Values |
|-------|--------|
| `decision` | `ALLOWED`, `REDACTED`, `BLOCKED` |
| `risk_score` | float 0–1 |
| `matched_patterns` | string[] |
| `redacted_body` | string \| null |
| `reason` | string \| null |
| `crystal_id` | string \| null |

### Demo policy (default)

| Pattern | Label | Action on `restricted` channel |
|---------|-------|--------------------------------|
| SSN `\d{3}-\d{2}-\d{4}` | `pii_ssn` | BLOCKED |
| API key `sk-[a-zA-Z0-9]{20,}` | `secret_api_key` | BLOCKED |
| Card `\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}` | `pii_pan` | REDACTED on `internal`; BLOCKED on `restricted` |

Unknown principal → BLOCKED.

## TCP / spine integration

- Platform id: `content_guard`
- Risk tier: `high`
- Policy id: `content-high-us`
- Facets: `principal_id`, `channel`, `classification_hint`, `decision`, `matched_patterns`, `risk_score`
- **Commit** when `decision` is `ALLOWED` or `REDACTED` (redacted body in facets)

## Threat Mesh

| Parent | Facet | Value | Blocks child |
|--------|-------|-------|--------------|
| `posture_reconcile` | `posture_state` | `STRANDED` | `content_guard` |
| `content_guard` | `content_decision` | `BLOCKED` | `egress_lock` |

## Deployment

```bash
CG_SPINE_ENABLED=false make content-guard-demo
docker compose up -d cg-content-guard
```

## Tests

- Unit: clean allow, SSN block, API key block, PAN redact
- Integration: `test_platforms_smoke`
- Mesh: BLOCKED content blocks egress (spine test)

## Competitive edge

**vs generic DLP:** mesh-aware — STRANDED posture or BLOCKED content **prevents egress commit** with crystal proof chain.
