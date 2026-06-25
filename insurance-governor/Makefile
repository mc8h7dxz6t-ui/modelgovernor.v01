.PHONY: ig-spine-up ig-spine-down ig-stack-up ig-stack-down ig-spine-test ig-spine-smoke claim-gate-demo ig-demo ig-certification ig-load-test ig-chaos-test ig-ha-up ig-ha-down ig-pilot-attestation bind-authority-demo parametric-oracle-demo

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

ig-load-test:
	cd .. && python3 -m pytest insurance-governor/tests/load/test_ig_load_harness.py -q

ig-certification:
	cd .. && python3 insurance-governor/scripts/generate_invariant_report.py

ig-chaos-test:
	cd .. && POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5436/ig_chaos \
	  TOXIPROXY_API=http://localhost:8475 \
	  PYTHONPATH=insurance-governor/spine/sidecar \
	  python3 -m pytest insurance-governor/tests/chaos/test_toxiproxy_claim_ops.py -q

ig-ha-up:
	docker compose -f docker-compose.ha.yml up -d --build --scale ig-sidecar=2 --scale ig-reconciler=2

ig-ha-down:
	docker compose -f docker-compose.ha.yml down

ig-pilot-attestation:
	chmod +x scripts/ig-pilot-attestation.sh
	cd .. && insurance-governor/scripts/ig-pilot-attestation.sh

bind-authority-demo:
	curl -sf http://localhost:8104/healthz
	curl -sf -X POST http://localhost:8104/bind/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"application_id":"demo-bind-1","premium":"10000.00","limit":"500000.00"}'

parametric-oracle-demo:
	curl -sf http://localhost:8105/healthz
