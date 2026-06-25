.PHONY: fg-spine-up fg-spine-down fg-spine-test fg-spine-smoke fg-spine-logs

fg-spine-up:
	cd finance-governor && docker compose up -d --build

fg-spine-down:
	cd finance-governor && docker compose down

fg-spine-logs:
	cd finance-governor && docker compose logs -f

fg-spine-test:
	cd finance-governor && python3 -m pytest tests/ -q

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
