.PHONY: ig-spine-up ig-spine-down ig-stack-up ig-stack-down ig-spine-test ig-spine-smoke claim-gate-demo ig-demo

ig-spine-up:
	docker compose -f docker-compose.spine.yml up -d --build

ig-stack-up:
	docker compose up -d --build

ig-spine-down:
	docker compose -f docker-compose.spine.yml down

ig-stack-down:
	docker compose down

ig-spine-test:
	cd .. && python3 -m pytest insurance-governor/tests/ -q

ig-spine-smoke:
	@echo "==> ig-sidecar health"
	curl -sf http://localhost:8101/healthz
	@echo "\n==> governed commit via gateway"
	curl -sf -X POST http://localhost:8100/governed/commit \
	  -H 'content-type: application/json' \
	  -d '{"platform":"claim_gate","operation_id":"smoke-1","facets":{"claim_id":"smoke-1","payout_amount":"100.00"},"policy_id":"claim-high-us","reserved_reserve":"50","committed_reserve":"50","outcome":"paid"}'
	@echo "\n==> verify chain"
	curl -sf -H 'x-internal-token: dev-ig-spine-token-change-me' \
	  http://localhost:8101/internal/claims/verify-chain
	@echo "\nig-spine-smoke OK"

claim-gate-demo:
	@echo "==> ClaimGate health (standalone: set IG_SPINE_ENABLED=false)"
	curl -sf http://localhost:8103/healthz
	@echo "\n==> auto-approve payout"
	curl -sf -X POST http://localhost:8103/claim/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"claim_id":"demo-1","payout_amount":"50000.00"}'
	@echo "\n==> HELD above threshold"
	curl -sf -X POST http://localhost:8103/claim/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"claim_id":"demo-2","payout_amount":"400000.00"}'
	@echo "\nclaim-gate-demo OK"

ig-demo: ig-spine-smoke claim-gate-demo
