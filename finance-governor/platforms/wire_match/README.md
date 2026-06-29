# WireMatch

Semantic wire gate — prevents fat-finger and beneficiary mismatch before SWIFT/API send.

## Standalone

```bash
# From repo root
docker compose -f finance-governor/platforms/wire_match/docker-compose.standalone.yml up --build
curl -sf http://localhost:8093/healthz
make -C finance-governor wirematch-demo
```

## Spine-connected

Set `FG_SPINE_ENABLED=true` and `FG_SIDECAR_URL` (see root `docker-compose.yml`).

## SDK

Uses `WIRE_MATCH_CONFIG` + `platform_configs.py` + `spine_helpers.crystallize_and_commit`.
