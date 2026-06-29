# AlgoFreeze

Algo deploy + feed integrity gate — blocks order egress on version mismatch or feed gap.

## Standalone

```bash
docker compose -f finance-governor/platforms/algofreeze/docker-compose.standalone.yml up --build
make -C finance-governor algofreeze-demo
```

## Spine

`FG_SPINE_ENABLED=true` enables crystallize/commit on freeze and routed orders.
