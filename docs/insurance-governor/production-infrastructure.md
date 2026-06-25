# Production Infrastructure — Mock to Live Transition

Guide for moving Insurance Governor from demo stubs to enterprise operations.

```
[ Mock Environment ] ──> Core stubs replaced ──> [ Live Production Infrastructure ]
                              ├── HA Postgres + PgBouncer (state)
                              ├── Live bank / oracle feeds (integrations)
                              └── Istio STRICT mTLS (mesh security)
```

---

## 1. Production state storage

### Problem
Platform modules used in-memory dicts (`payment_idempotency`, `claim_commitments`) — lost on restart, not HA-safe.

### Solution
Migration **`0008_production_state.sql`** creates durable tables:

| Table | Replaces | Purpose |
|-------|----------|---------|
| `payment_idempotency` | `payment_rail._IDEMPOTENCY` | Idempotent payout instructions |
| `claim_commitments` | `zk_claim_audit._COMMITMENTS` | ZK audit fact seals |
| `oracle_feed_cache` | — | Optional feed dedup / audit |

### Wiring
```yaml
# Helm platform pods (all 11 platforms)
env:
  IG_PLATFORM_DATABASE_URL: <from secret via PgBouncer>
```

```bash
# Local compose
IG_PLATFORM_DATABASE_URL=postgresql+psycopg://postgres:postgres@ig-postgres:5432/insurancegovernor
```

**HA path:** `values-production.yaml` → PgBouncer `6432` → Postgres 16 (managed RDS/Aurora recommended).

```bash
make ig-ha-up   # PgBouncer rehearsal compose
```

Code: `platforms/common/persistence/` — auto-selects Postgres when `DATABASE_URL` / `IG_PLATFORM_DATABASE_URL` is set; falls back to memory for unit tests.

---

## 2. Live third-party integrations

### Payment rail (ACH stub → FedNow / clearinghouse)

| Env var | Values | Purpose |
|---------|--------|---------|
| `PAYMENT_RAIL_MODE` | `stub` \| `fednow` \| `clearinghouse` | Rail selection |
| `FEDNOW_API_URL` | HTTPS endpoint | FedNow instant payment API |
| `CLEARINGHOUSE_API_URL` | HTTPS endpoint | ACH / TCH clearinghouse |
| `BANK_RAIL_API_TOKEN` | Bearer token | mTLS companion via Istio egress |

Code: `platforms/common/integrations/bank_rail.py`

Production values (`values-production.yaml`):
```yaml
integrations:
  paymentRailMode: fednow
```

### Oracle / weather feeds (mock → live)

| Env var | Values | Purpose |
|---------|--------|---------|
| `ORACLE_FEED_MODE` | `mock` \| `live` | Feed mode |
| `ORACLE_FEED_SOURCE` | `usgs-live`, `noaa-weather`, `chainlink` | Provider |
| `ORACLE_FEED_URL` | Custom HTTP | Chainlink / private oracle |
| `ORACLE_FEED_API_KEY` | API key | Authenticated feeds |
| `USGS_FEED_URL` | USGS GeoJSON | Public earthquake stream |
| `NOAA_API_URL` | NWS endpoint | Meteorological parametric |

Code: `platforms/common/integrations/oracle_providers.py`

```yaml
integrations:
  oracleFeedMode: live
  oracleFeedSource: usgs-live
```

---

## 3. Istio mTLS hardening

### Enable (production overlay)
```yaml
enterprise:
  istio:
    enabled: true
    mtlsMode: STRICT
    egress:
      bankRails:
        - api.fednowgateway.frb.org
      oracleFeeds:
        - earthquake.usgs.gov
        - api.chain.link
```

Helm renders (`templates/istio-enterprise.yaml`):
- **PeerAuthentication** — STRICT mTLS namespace-wide
- **DestinationRule** — `ISTIO_MUTUAL` for `*.insurancegovernor.svc.cluster.local`
- **ServiceEntry** — bank + oracle external hosts
- **AuthorizationPolicy** — platform egress allowlist

Pod injection (`sidecar.istio.io/inject: "true"`) on:
- Gateway, sidecar, reconciler
- **All 11 platform deployments**

```bash
helm lint deploy/helm/insurancegovernor -f deploy/helm/insurancegovernor/values-production.yaml
```

---

## 4. Deployment checklist

| Step | Command / action |
|------|------------------|
| Run migrations | Helm pre-sync job includes `0008_production_state.sql` |
| Populate secrets | `database-url`, `BANK_RAIL_API_TOKEN`, `ORACLE_FEED_API_KEY` via ExternalSecrets |
| Set integration mode | `values-production.yaml` → `integrations.*` |
| Enable Istio | `enterprise.istio.enabled: true` |
| Verify state | Payment idempotency survives pod restart |
| Verify mesh | `istioctl authn tls-check <pod>` |
| Attestation | `make ig-certification` |

---

## 5. Environment matrix

| Environment | `PAYMENT_RAIL_MODE` | `ORACLE_FEED_MODE` | Istio | Database |
|-------------|---------------------|--------------------|-------|----------|
| Local demo | `stub` | `mock` | off | optional |
| Staging | `stub` | `live` | optional | PgBouncer |
| Production | `fednow` | `live` | STRICT | HA Postgres + PgBouncer |

---

## Related

- [institutional-gold-standard.md](institutional-gold-standard.md)
- Helm: `deploy/helm/insurancegovernor/values-production.yaml`
- HA compose: `insurance-governor/docker-compose.ha.yml`
