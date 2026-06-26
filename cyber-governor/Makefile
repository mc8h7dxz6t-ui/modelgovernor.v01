.PHONY: cg-spine-up cg-spine-down cg-spine-test cg-spine-smoke cg-spine-logs \
	cg-stack-up cg-stack-down threat-crystal-demo identity-gate-demo egress-lock-demo witness-bridge-demo

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
