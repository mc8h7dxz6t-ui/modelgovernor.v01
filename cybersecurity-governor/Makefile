.PHONY: cg-spine-up cg-spine-down cg-stack-up cg-stack-down cg-spine-test cg-spine-smoke claim-gate-demo cg-demo cg-certification cg-certification-strict cg-certification-l4 cg-certification-l4-ci cg-helm-enterprise cg-platform-conformance cg-load-test cg-chaos-test cg-ha-up cg-ha-down cg-pilot-attestation cg-cluster-attestation cg-rail-smoke cg-design-partner-package ig-claim-gate-load cg-full-rehearsal cg-embedded-rehearsal cg-examiner-evidence bind-authority-demo parametric-oracle-demo

cg-spine-up:
	docker compose -f docker-compose.spine.yml up -d --build

cg-stack-up:
	docker compose up -d --build

cg-spine-down:
	docker compose -f docker-compose.spine.yml down

cg-stack-down:
	docker compose down

cg-spine-test:
	cd .. && python3 -m pytest cybersecurity-governor/tests/ -q

cg-spine-smoke:
	@echo "==> cg-sidecar health"
	curl -sf http://localhost:8121/healthz
	@echo "\n==> governed commit via gateway"
	curl -sf -X POST http://localhost:8120/governed/commit \
	  -H 'content-type: application/json' \
	  -d '{"platform":"egress_govern","operation_id":"smoke-1","facets":{"flow_id":"smoke-1","destination_host":"api.openai.com","egress_decision":"ALLOWED"},"policy_id":"egress-critical-us","reserved_budget":"0","committed_budget":"0","outcome":"allowed"}'
	@echo "\n==> verify chain"
	curl -sf -H 'x-internal-token: dev-cg-spine-token-change-me' \
	  http://localhost:8121/internal/security/verify-chain
	@echo "\ncg-spine-smoke OK"

egress-govern-demo:
	@echo "==> EgressGovern health (standalone: set CG_SPINE_ENABLED=false)"
	curl -sf http://localhost:8123/healthz
	@echo "\n==> allowlisted egress"
	curl -sf -X POST http://localhost:8123/egress/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"flow_id":"demo-1","destination_host":"api.openai.com"}'
	@echo "\n==> DENIED off-allowlist"
	curl -sf -X POST http://localhost:8123/egress/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"flow_id":"demo-2","destination_host":"evil.example.com"}' || true
	@echo "\negress-govern-demo OK"

cg-demo: cg-spine-smoke egress-govern-demo

cg-load-test:
	cd .. && python3 -m pytest cybersecurity-governor/tests/load/test_cg_load_harness.py -q

cg-certification:
	cd .. && python3 cybersecurity-governor/scripts/generate_invariant_report.py

cg-certification-strict:
	@echo "==> Strict L4 Gold gate (no skip fallbacks)"
	@$(MAKE) cg-certification
	@echo "==> Tier 4 chaos (requires docker-compose.chaos.yml)"
	@$(MAKE) cg-chaos-test
	@echo "==> Live chain verify (requires cg-stack-up)"
	@curl -sf -H 'x-internal-token: dev-cg-spine-token-change-me' \
	  http://localhost:8121/internal/security/verify-chain \
	  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d"
	@echo "cg-certification-strict complete"

cg-examiner-evidence:
	chmod +x scripts/cg_examiner_evidence_pack.py
	cd .. && python3 cybersecurity-governor/scripts/cg_examiner_evidence_pack.py

cg-helm-enterprise:
	helm template ig ../deploy/helm/cybersecuritygovernor \
	  -f ../deploy/helm/cybersecuritygovernor/values-production.yaml \
	  -f ../deploy/helm/cybersecuritygovernor/values-enterprise.yaml \
	  --set secrets.create=true \
	  --set secrets.postgresPassword=postgres

cg-certification-l4-ci:
	@echo "==> L4 Gold CI gate (reliability + enterprise manifests)"
	cd .. && PYTHONPATH=cybersecurity-governor/spine/sidecar:cybersecurity-governor/tests:cybersecurity-governor python3 -m pytest \
	  cybersecurity-governor/tests/test_l4_helm_enterprise.py \
	  cybersecurity-governor/tests/test_l4_certification.py \
	  cybersecurity-governor/tests/test_horizon_sweeper.py \
	  cybersecurity-governor/tests/test_commit_invariants.py \
	  cybersecurity-governor/tests/test_security_seal_failclosed.py \
	  cybersecurity-governor/tests/test_platform_registry_failclosed.py \
	  cybersecurity-governor/tests/test_regulatory_export.py -q
	@$(MAKE) cg-helm-enterprise > /dev/null
	@echo "cg-certification-l4-ci complete"

cg-certification-l4:
	@echo "==> L4 Gold certification gate"
	@$(MAKE) cg-certification
	@echo "==> L4 Helm enterprise render"
	@$(MAKE) cg-helm-enterprise > /dev/null
	@echo "==> L4 Helm enterprise tests"
	cd .. && PYTHONPATH=cybersecurity-governor/spine/sidecar python3 -m pytest \
	  cybersecurity-governor/tests/test_l4_helm_enterprise.py \
	  cybersecurity-governor/tests/test_l4_certification.py -q
	@$(MAKE) cg-examiner-evidence
	@echo "cg-certification-l4 complete (L4 Gold)"

cg-platform-conformance:
	cd .. && PYTHONPATH=cybersecurity-governor/spine/sidecar python3 -m pytest \
	  cybersecurity-governor/tests/test_platform_sdk.py \
	  cybersecurity-governor/tests/test_platform_invariant_counters.py \
	  cybersecurity-governor/tests/test_headline_wedges.py \
	  cybersecurity-governor/tests/test_loss_control_wedges.py -q

cg-chaos-test:
	cd .. && POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5436/cg_chaos \
	  TOXIPROXY_API=http://localhost:8475 \
	  PYTHONPATH=cybersecurity-governor/spine/sidecar \
	  python3 -m pytest cybersecurity-governor/tests/chaos/test_toxiproxy_security_ops.py -q

cg-ha-up:
	docker compose -f docker-compose.ha.yml up -d --build --scale ig-sidecar=2 --scale ig-reconciler=2

cg-ha-down:
	docker compose -f docker-compose.ha.yml down

cg-pilot-attestation:
	chmod +x scripts/cg-pilot-attestation.sh scripts/attestation_runner.py
	cd .. && cybersecurity-governor/scripts/cg-pilot-attestation.sh

cg-cluster-attestation:
	chmod +x scripts/cg-cluster-attestation.sh
	cd .. && cybersecurity-governor/scripts/cg-cluster-attestation.sh

cg-rail-smoke:
	chmod +x scripts/cg-rail-smoke.sh
	cd .. && cybersecurity-governor/scripts/cg-rail-smoke.sh

cg-design-partner-package:
	cd .. && python3 cybersecurity-governor/scripts/generate_design_partner_attestation.py

ig-claim-gate-load:
	cd .. && python3 -m pytest cybersecurity-governor/tests/load/test_claim_gate_production.py -q

cg-full-rehearsal:
	chmod +x scripts/cg-full-rehearsal.sh scripts/mock_fednow_sandbox.py scripts/publish_data_room.py scripts/attestation_embedded_rehearsal.py
	cd .. && cybersecurity-governor/scripts/cg-full-rehearsal.sh

cg-embedded-rehearsal:
	chmod +x scripts/attestation_embedded_rehearsal.py scripts/publish_data_room.py
	cd .. && \
	  CG_ATTESTATION_ENV=local-embedded-rehearsal \
	  python3 cybersecurity-governor/scripts/attestation_embedded_rehearsal.py && \
	  python3 cybersecurity-governor/scripts/attestation_validate.py && \
	  (make cg-certification || true) && \
	  python3 cybersecurity-governor/scripts/generate_design_partner_attestation.py && \
	  python3 cybersecurity-governor/scripts/publish_data_room.py

bind-authority-demo:
	curl -sf http://localhost:8104/healthz
	curl -sf -X POST http://localhost:8104/bind/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"application_id":"demo-bind-1","premium":"10000.00","limit":"500000.00"}'

parametric-oracle-demo:
	curl -sf http://localhost:8105/healthz
