# CreditGovern

Credit decision governance — reserve-before-score, live inference rails, bias cohort hooks.

## Standalone

```bash
docker compose -f finance-governor/platforms/credit_govern/docker-compose.standalone.yml up --build
make -C finance-governor credit-demo
```

## Live rails

| Env | Purpose |
|-----|---------|
| `FG_CREDIT_RAIL_MODE` | `mock`, `live`, or `auto` |
| `FG_CREDIT_RAIL_PROVIDER` | `http`, `sagemaker`, or `vertex` |
| `FG_CREDIT_RAIL_URL` | Endpoint base URL |

Full stack with reference rail: root `docker-compose.yml` (`fg-credit-rail` on :8098).
