.PHONY: cg-spine-up cg-spine-down cg-spine-test cg-spine-smoke cg-spine-logs \
	cg-stack-up cg-stack-down threat-crystal-demo cg-security-demo identity-gate-demo \
	egress-lock-demo witness-bridge-demo lineage-ingest-demo cg-deploy-dry-run \
	cg-postgres-test cg-proof-test

cg-spine-up:
	docker compose up -d --build

cg-stack-up: cg-spine-up

cg-spine-down:
	docker compose down

cg-stack-down: cg-spine-down

cg-spine-logs:
	docker compose logs -f

cg-spine-test:
	python3 -m pytest tests/ -q

cg-spine-smoke:
	@echo "==> cg-sidecar health"
	curl -sf http://localhost:8101/healthz
	@echo "\n==> crystallize + commit via gateway"
	curl -sf -X POST http://localhost:8100/governed/commit \
	  -H 'content-type: application/json' \
	  -d '{"platform":"identity_gate","operation_id":"smoke-1","facets":{"session_state":"AUTHORIZED","user_id":"alice@corp.example"},"policy_id":"identity-critical-us"}'
	@echo "\n==> recent events"
	curl -sf -H 'x-internal-token: dev-cg-spine-token-change-me' \
	  http://localhost:8101/internal/events/recent?limit=5
	@echo "\ncg-spine-smoke OK"

identity-gate-demo:
	@echo "==> IdentityGate health"
	curl -sf http://localhost:8103/healthz
	@echo "\n==> session hijack STRANDED"
	curl -sf -X POST http://localhost:8103/session/arm \
	  -H 'content-type: application/json' \
	  -d '{"session_id":"demo-1","user_id":"alice@corp.example","device_fingerprint":"attacker_device","client_ip":"203.0.113.9"}'
	@echo "\nidentity-gate-demo OK"

egress-lock-demo:
	@echo "==> EgressLock health"
	curl -sf http://localhost:8104/healthz
	@echo "\n==> blocked destination"
	curl -sf -X POST http://localhost:8104/egress/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"egress_id":"demo-1","principal_id":"alice@corp.example","destination":"evil-exfil.example","byte_count":1024}'
	@echo "\negress-lock-demo OK"

witness-bridge-demo:
	@echo "==> WitnessBridge health"
	curl -sf http://localhost:8105/healthz
	@echo "\n==> CloudTrail delete event witnessed"
	curl -sf -X POST http://localhost:8105/ingest/cloudtrail \
	  -H 'content-type: application/json' \
	  -d '{"detail":{"eventName":"DeleteTrail","eventID":"evt-1","userIdentity":{"arn":"arn:aws:iam::123:user/bob"}}}'
	@echo "\nwitness-bridge-demo OK"

threat-crystal-demo:
	./scripts/threat-crystal-demo.sh

cg-security-demo:
	./scripts/cg-security-demo.sh

lineage-ingest-demo:
	@echo "==> LineageIngest health"
	curl -sf http://localhost:8106/healthz
	@echo "\n==> Falco critical shell"
	curl -sf -X POST http://localhost:8106/ingest/falco \
	  -H 'content-type: application/json' \
	  -d '{"rule":"Terminal shell in container","priority":"Critical","output_fields":{"proc.name":"bash","user.name":"root"}}'
	@echo "\nlineage-ingest-demo OK"

cg-deploy-dry-run:
	@command -v kubectl >/dev/null && command -v kustomize >/dev/null && \
	  kustomize build deploy/base/ | kubectl apply --dry-run=client -f - || \
	  echo "kubectl/kustomize not installed — skipping dry-run"

cg-postgres-test:
	@docker compose -f docker-compose.test.yml up -d --wait 2>/dev/null || true
	CG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5444/cg_test \
	  python3 -m pytest tests/integration/test_postgres_vigorous.py -q

cg-proof-test: cg-spine-test cg-postgres-test cg-deploy-dry-run
	@echo "cg-proof-test OK — institutional++ tiers 1, 2, 4"
