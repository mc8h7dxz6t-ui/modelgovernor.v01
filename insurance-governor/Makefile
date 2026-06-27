.PHONY: ig-spine-up ig-spine-down ig-stack-up ig-stack-down ig-spine-test ig-spine-smoke claim-gate-demo ig-demo ig-certification ig-certification-strict ig-certification-l4 ig-certification-l4-ci ig-helm-enterprise ig-platform-conformance ig-load-test ig-chaos-test ig-ha-up ig-ha-down ig-pilot-attestation ig-cluster-attestation ig-rail-smoke ig-design-partner-package ig-claim-gate-load ig-full-rehearsal ig-embedded-rehearsal ig-examiner-evidence bind-authority-demo parametric-oracle-demo

ig-spine-up:
	docker compose -f docker-compose.spine.yml up -d --build

ig-stack-up:
	docker compose up -d --build

ig-spine-down:
	docker compose -f docker-compose.spine.yml down

ig-stack-down:
	docker compose down

ig-spine-test:
	cd .. && PYTHONPATH=insurance-governor/spine/sidecar:insurance-governor/tests:insurance-governor python3 -m pytest \
	  insurance-governor/tests/ -q \
	  --ignore=insurance-governor/tests/chaos \
	  --ignore=insurance-governor/tests/load \
	  --ignore=insurance-governor/tests/integration

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
	cd .. && PYTHONPATH=insurance-governor/spine/sidecar:insurance-governor/tests:insurance-governor python3 -m pytest insurance-governor/tests/load/test_ig_load_harness.py -q

ig-certification:
	cd .. && python3 insurance-governor/scripts/generate_invariant_report.py

ig-certification-strict:
	@echo "==> Strict L4 Gold gate (no skip fallbacks)"
	@$(MAKE) ig-certification
	@echo "==> Tier 4 chaos (requires docker-compose.chaos.yml)"
	@$(MAKE) ig-chaos-test
	@echo "==> Live chain verify (requires ig-stack-up)"
	@curl -sf -H 'x-internal-token: dev-ig-spine-token-change-me' \
	  http://localhost:8101/internal/claims/verify-chain \
	  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d"
	@echo "ig-certification-strict complete"

ig-examiner-evidence:
	chmod +x scripts/ig_examiner_evidence_pack.py
	cd .. && python3 insurance-governor/scripts/ig_examiner_evidence_pack.py

ig-helm-enterprise:
	helm template ig ../deploy/helm/insurancegovernor \
	  -f ../deploy/helm/insurancegovernor/values-production.yaml \
	  -f ../deploy/helm/insurancegovernor/values-enterprise.yaml \
	  --set secrets.create=true \
	  --set secrets.postgresPassword=postgres

ig-certification-l4-ci:
	@echo "==> L4 Gold CI gate (reliability + enterprise manifests)"
	cd .. && PYTHONPATH=insurance-governor/spine/sidecar:insurance-governor/tests:insurance-governor python3 -m pytest \
	  insurance-governor/tests/test_l4_helm_enterprise.py \
	  insurance-governor/tests/test_l4_certification.py \
	  insurance-governor/tests/test_horizon_sweeper.py \
	  insurance-governor/tests/test_commit_invariants.py \
	  insurance-governor/tests/test_claim_seal_failclosed.py \
	  insurance-governor/tests/test_platform_registry_failclosed.py \
	  insurance-governor/tests/test_regulatory_export.py -q
	@$(MAKE) ig-helm-enterprise > /dev/null
	@echo "ig-certification-l4-ci complete"

ig-certification-l4:
	@echo "==> L4 Gold certification gate"
	@$(MAKE) ig-certification
	@echo "==> L4 Helm enterprise render"
	@$(MAKE) ig-helm-enterprise > /dev/null
	@echo "==> L4 Helm enterprise tests"
	cd .. && PYTHONPATH=insurance-governor/spine/sidecar python3 -m pytest \
	  insurance-governor/tests/test_l4_helm_enterprise.py \
	  insurance-governor/tests/test_l4_certification.py -q
	@$(MAKE) ig-examiner-evidence
	@echo "ig-certification-l4 complete (L4 Gold)"

ig-platform-conformance:
	cd .. && PYTHONPATH=insurance-governor/spine/sidecar python3 -m pytest \
	  insurance-governor/tests/test_platform_sdk.py \
	  insurance-governor/tests/test_platform_invariant_counters.py \
	  insurance-governor/tests/test_headline_wedges.py \
	  insurance-governor/tests/test_loss_control_wedges.py -q

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
	chmod +x scripts/ig-pilot-attestation.sh scripts/attestation_runner.py
	cd .. && insurance-governor/scripts/ig-pilot-attestation.sh

ig-cluster-attestation:
	chmod +x scripts/ig-cluster-attestation.sh
	cd .. && insurance-governor/scripts/ig-cluster-attestation.sh

ig-rail-smoke:
	chmod +x scripts/ig-rail-smoke.sh
	cd .. && insurance-governor/scripts/ig-rail-smoke.sh

ig-design-partner-package:
	cd .. && python3 insurance-governor/scripts/generate_design_partner_attestation.py

ig-claim-gate-load:
	cd .. && python3 -m pytest insurance-governor/tests/load/test_claim_gate_production.py -q

ig-full-rehearsal:
	chmod +x scripts/ig-full-rehearsal.sh scripts/mock_fednow_sandbox.py scripts/publish_data_room.py scripts/attestation_embedded_rehearsal.py
	cd .. && insurance-governor/scripts/ig-full-rehearsal.sh

ig-embedded-rehearsal:
	chmod +x scripts/attestation_embedded_rehearsal.py scripts/publish_data_room.py
	cd .. && \
	  IG_ATTESTATION_ENV=local-embedded-rehearsal \
	  python3 insurance-governor/scripts/attestation_embedded_rehearsal.py && \
	  python3 insurance-governor/scripts/attestation_validate.py && \
	  (make ig-certification || true) && \
	  python3 insurance-governor/scripts/generate_design_partner_attestation.py && \
	  python3 insurance-governor/scripts/publish_data_room.py

bind-authority-demo:
	curl -sf http://localhost:8104/healthz
	curl -sf -X POST http://localhost:8104/bind/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"application_id":"demo-bind-1","premium":"10000.00","limit":"500000.00"}'

parametric-oracle-demo:
	curl -sf http://localhost:8105/healthz
