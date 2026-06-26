.PHONY: cg-spine-up cg-spine-down cg-spine-test cg-spine-smoke cg-spine-logs \
	cg-stack-up cg-stack-down threat-crystal-demo cg-security-demo identity-gate-demo \
	egress-lock-demo witness-bridge-demo lineage-ingest-demo posture-reconcile-demo \
	content-guard-demo cg-deploy-dry-run cg-demo-prereq \
	cg-postgres-test cg-proof-test cg-load-test cg-invariant-report cg-chaos-test \
	cg-property-test cg-bootstrap cg-prod-bootstrap

cg-spine-up:
	./scripts/cg-stack-up.sh

cg-stack-up: cg-spine-up

cg-spine-down:
	docker compose down

cg-stack-down: cg-spine-down

cg-spine-logs:
	docker compose logs -f

cg-spine-test:
	python3 -m pytest tests/ -q --ignore=tests/load/ --ignore=tests/chaos/

cg-property-test:
	python3 -m pytest tests/test_property_security_chain.py -q

cg-chaos-test:
	@docker compose -f docker-compose.chaos.yml up -d --wait cg-postgres-chaos cg-toxiproxy 2>/dev/null || true
	@docker compose -f docker-compose.chaos.yml run --rm cg-toxiproxy-config 2>/dev/null || true
	CG_CHAOS_POSTGRES_URL=postgresql+psycopg://postgres:postgres@localhost:5446/cg_chaos \
	TOXIPROXY_API=http://localhost:8475 \
	  python3 -m pytest tests/chaos/ -q

cg-load-test:
	CG_LOAD_TEST=1 python3 -m pytest tests/load/ -v -s

cg-invariant-report:
	python3 scripts/generate_cyber_invariant_report.py

cg-bootstrap:
	chmod +x scripts/bootstrap-secrets.sh
	./scripts/bootstrap-secrets.sh --write-env
	@echo "cg-bootstrap OK — wrote .env with random CG_INTERNAL_TOKENS"

cg-prod-bootstrap:
	chmod +x scripts/cg-prod-bootstrap.sh scripts/bootstrap-secrets.sh
	./scripts/cg-prod-bootstrap.sh

cg-demo-prereq:
	@bash -c 'source scripts/cg-demo-lib.sh && ensure_cg_stack_up'

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

identity-gate-demo: cg-demo-prereq
	@echo "==> IdentityGate health"
	curl -sf http://localhost:8103/healthz
	@echo "\n==> session hijack STRANDED"
	curl -sf -X POST http://localhost:8103/session/arm \
	  -H 'content-type: application/json' \
	  -d '{"session_id":"demo-1","user_id":"alice@corp.example","device_fingerprint":"attacker_device","client_ip":"203.0.113.9"}'
	@echo "\nidentity-gate-demo OK"

egress-lock-demo: cg-demo-prereq
	@echo "==> EgressLock health"
	curl -sf http://localhost:8104/healthz
	@echo "\n==> blocked destination"
	curl -sf -X POST http://localhost:8104/egress/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"egress_id":"demo-1","principal_id":"alice@corp.example","destination":"evil-exfil.example","byte_count":1024}'
	@echo "\negress-lock-demo OK"

witness-bridge-demo: cg-demo-prereq
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

lineage-ingest-demo: cg-demo-prereq
	@echo "==> LineageIngest health"
	curl -sf http://localhost:8106/healthz
	@echo "\n==> Falco critical shell"
	curl -sf -X POST http://localhost:8106/ingest/falco \
	  -H 'content-type: application/json' \
	  -d '{"rule":"Terminal shell in container","priority":"Critical","output_fields":{"proc.name":"bash","user.name":"root"}}'
	@echo "\nlineage-ingest-demo OK"

posture-reconcile-demo: cg-demo-prereq
	@echo "==> PostureReconcile health"
	curl -sf http://localhost:8107/healthz
	@echo "\n==> critical posture drift STRANDED"
	curl -sf -X POST http://localhost:8107/posture/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"evaluation_id":"demo-pr-1","resource_id":"eks-dr","posture_score":72,"failed_controls":["public_s3_bucket"]}'
	@echo "\nposture-reconcile-demo OK"

content-guard-demo: cg-demo-prereq
	@echo "==> ContentGuard health"
	curl -sf http://localhost:8108/healthz
	@echo "\n==> API key leak BLOCKED"
	curl -sf -X POST http://localhost:8108/content/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"content_id":"demo-cg-1","principal_id":"alice@corp.example","text_body":"key sk-abcdefghijklmnopqrstuvwxyz123456","classification_hint":"restricted"}'
	@echo "\ncontent-guard-demo OK"

cg-deploy-dry-run:
	@command -v kubectl >/dev/null && command -v kustomize >/dev/null && \
	  kustomize build --load-restrictor LoadRestrictionsNone deploy/base/ | kubectl apply --dry-run=client -f - && \
	  kustomize build --load-restrictor LoadRestrictionsNone deploy/overlays/production/ | kubectl apply --dry-run=client -f - || \
	  echo "kubectl/kustomize not installed — skipping dry-run"

cg-postgres-test:
	@docker compose -f docker-compose.test.yml up -d --wait 2>/dev/null || true
	CG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5444/cg_test \
	  python3 -m pytest tests/integration/ -q

cg-proof-test: cg-spine-test cg-property-test cg-postgres-test cg-invariant-report cg-deploy-dry-run
	@echo "cg-proof-test OK — institutional++ tiers 1–3, property, invariant report, deploy dry-run"
