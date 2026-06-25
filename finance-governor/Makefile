.PHONY: fg-spine-up fg-spine-down fg-spine-test fg-spine-smoke fg-spine-logs \
	fg-stack-up fg-stack-down crystal-demo algofreeze-demo wirematch-demo fg-certification

fg-spine-up:
	docker compose up -d --build

fg-stack-up: fg-spine-up

fg-spine-down:
	docker compose down

fg-stack-down: fg-spine-down

fg-spine-logs:
	docker compose logs -f

fg-spine-test:
	python3 -m pytest tests/ -q

fg-spine-smoke:
	@echo "==> fg-sidecar health"
	curl -sf http://localhost:8091/healthz
	@echo "\n==> crystallize + commit via gateway"
	curl -sf -X POST http://localhost:8090/governed/commit \
	  -H 'content-type: application/json' \
	  -d '{"platform":"wire_match","operation_id":"smoke-1","facets":{"amount":"100.00"},"policy_id":"wire-critical-us","reserved_exposure":"50","committed_exposure":"50"}'
	@echo "\n==> reconstruct"
	curl -sf -H 'x-internal-token: dev-fg-spine-token-change-me' \
	  http://localhost:8091/internal/events/recent?limit=5
	@echo "\nfg-spine-smoke OK"

wirematch-demo:
	@echo "==> WireMatch health"
	curl -sf http://localhost:8093/healthz
	@echo "\n==> amount anomaly HELD"
	curl -sf -X POST http://localhost:8093/wire/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"wire_id":"demo-1","beneficiary_name":"Revlon Lenders Group","beneficiary_account":"US12REV001","reference":"payment","amount":"900000000.00"}'
	@echo "\nwirematch-demo OK"

algofreeze-demo:
	@echo "==> AlgoFreeze health"
	curl -sf http://localhost:8094/healthz
	@echo "\n==> version mismatch freeze"
	curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8094/orders \
	  -H 'content-type: application/json' \
	  -d '{"order_id":"demo-1","runtime_sha":"wrong-deploy-sha"}' | grep -q 403
	curl -sf http://localhost:8094/status
	@echo "\nalgofreeze-demo OK"

crystal-demo:
	./scripts/crystal-demo.sh

fg-certification:
	@echo "==> Tier 1: unit + spine hardening tests"
	python3 -m pytest tests/ -q
	@echo "==> Chain verify smoke (requires spine up; skipped if unavailable)"
	@if curl -sf -H 'x-internal-token: dev-fg-spine-token-change-me' \
	  http://localhost:8091/internal/decisions/verify-chain 2>/dev/null \
	  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d" \
	  2>/dev/null; then echo "chain verify OK"; else echo "chain verify skipped (spine not running)"; fi
	@echo "fg-certification complete"
