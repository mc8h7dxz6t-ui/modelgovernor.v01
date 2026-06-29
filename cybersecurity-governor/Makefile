.PHONY: cg-spine-up cg-spine-down cg-stack-up cg-stack-down cg-spine-test cg-spine-smoke cg-property-test egress-govern-demo cg-demo cg-security-demo cg-egress-wedge-demo posture-reconcile-demo content-guard-demo cg-certification cg-certification-strict cg-certification-l4 cg-certification-l4-ci cg-helm-enterprise cg-platform-conformance cg-load-test cg-chaos-test cg-ha-up cg-ha-down cg-pilot-attestation cg-design-partner-package cg-examiner-evidence cg-test-deps

cg-test-deps:
	python3 -m pip install --upgrade pip
	python3 -m pip install \
	  -r spine/sidecar/requirements.txt \
	  -r spine/gateway/requirements.txt \
	  -r spine/reconciler/requirements.txt \
	  -r platforms/requirements.txt \
	  pytest pyyaml httpx

cg-spine-up:
	docker compose -f docker-compose.spine.yml up -d --build

cg-stack-up:
	docker compose up -d --build

cg-spine-down:
	docker compose -f docker-compose.spine.yml down

cg-stack-down:
	docker compose down

cg-spine-test:
	cd .. && PYTHONPATH=governor-spine-core:cybersecurity-governor/spine/sidecar:cybersecurity-governor/tests:cybersecurity-governor python3 -m pytest \
	  cybersecurity-governor/tests/ -q \
	  --ignore=cybersecurity-governor/tests/chaos \
	  --ignore=cybersecurity-governor/tests/load

cg-property-test:
	cd .. && PYTHONPATH=governor-spine-core:cybersecurity-governor/spine/sidecar:cybersecurity-governor/tests:cybersecurity-governor python3 -m pytest \
	  cybersecurity-governor/tests/test_property_security_chain.py -q

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

posture-reconcile-demo:
	@echo "==> PostureReconcile health (8127)"
	curl -sf http://localhost:8127/healthz
	@echo "\n==> posture within tolerance"
	curl -sf -X POST http://localhost:8127/posture/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"asset_id":"demo-ok","critical_cves":0,"patch_lag_days":5}'
	@echo "\n==> DRIFT (critical CVEs)"
	curl -sf -X POST http://localhost:8127/posture/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"asset_id":"demo-drift","critical_cves":3,"patch_lag_days":60}' || true
	@echo "\nposture-reconcile-demo OK"

content-guard-demo:
	@echo "==> ContentGuard health (8131)"
	curl -sf http://localhost:8131/healthz
	@echo "\n==> clean content allowed"
	curl -sf -X POST http://localhost:8131/content/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"content_id":"demo-clean","principal_id":"alice@corp.example","text_body":"quarterly report summary"}'
	@echo "\n==> API key leak blocked"
	curl -sf -X POST http://localhost:8131/content/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"content_id":"demo-leak","principal_id":"alice@corp.example","text_body":"key sk-abcdefghijklmnopqrstuvwxyz123456"}' \
	  || echo '{"decision":"BLOCKED"}'
	@echo "\ncontent-guard-demo OK"

cg-demo: cg-spine-smoke egress-govern-demo

cg-security-demo:
	chmod +x scripts/cg-security-demo.sh
	cd .. && cybersecurity-governor/scripts/cg-security-demo.sh

cg-egress-wedge-demo:
	chmod +x scripts/cg-egress-wedge-demo.sh
	cd .. && cybersecurity-governor/scripts/cg-egress-wedge-demo.sh

cg-load-test:
	cd .. && PYTHONPATH=governor-spine-core:cybersecurity-governor/spine/sidecar:cybersecurity-governor/tests:cybersecurity-governor python3 -m pytest cybersecurity-governor/tests/load/test_cg_load_harness.py -q

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
	helm template cg ../deploy/helm/cybersecuritygovernor \
	  -f ../deploy/helm/cybersecuritygovernor/values-production.yaml \
	  -f ../deploy/helm/cybersecuritygovernor/values-enterprise.yaml \
	  --set secrets.create=true \
	  --set secrets.postgresPassword=postgres

cg-certification-l4-ci:
	@echo "==> L4 Gold CI gate (artifact presence + runtime enforcement + deploy kit)"
	cd .. && PYTHONPATH=governor-spine-core:cybersecurity-governor/spine/sidecar:cybersecurity-governor/tests:cybersecurity-governor python3 -m pytest \
	  cybersecurity-governor/tests/test_l4_helm_enterprise.py \
	  cybersecurity-governor/tests/test_l4_artifacts_present.py \
	  cybersecurity-governor/tests/test_l4_runtime_enforcement.py \
	  cybersecurity-governor/tests/test_horizon_sweeper.py \
	  cybersecurity-governor/tests/test_commit_invariants.py \
	  cybersecurity-governor/tests/test_security_seal_failclosed.py \
	  cybersecurity-governor/tests/test_incremental_chain_verify.py \
	  cybersecurity-governor/tests/test_platform_registry_failclosed.py \
	  cybersecurity-governor/tests/test_regulatory_export.py -q
	@$(MAKE) cg-helm-enterprise > /dev/null
	@echo "cg-certification-l4-ci complete"

cg-certification-l4:
	@echo "==> L4 Gold certification gate"
	@$(MAKE) cg-certification
	@echo "==> L4 Helm enterprise render"
	@$(MAKE) cg-helm-enterprise > /dev/null
	@echo "==> L4 Helm enterprise + runtime tests"
	cd .. && PYTHONPATH=governor-spine-core:cybersecurity-governor/spine/sidecar:cybersecurity-governor/tests:cybersecurity-governor python3 -m pytest \
	  cybersecurity-governor/tests/test_l4_helm_enterprise.py \
	  cybersecurity-governor/tests/test_l4_artifacts_present.py \
	  cybersecurity-governor/tests/test_l4_runtime_enforcement.py -q
	@$(MAKE) cg-examiner-evidence
	@echo "cg-certification-l4 complete (L4 Gold)"

cg-platform-conformance:
	cd .. && PYTHONPATH=governor-spine-core:cybersecurity-governor/spine/sidecar:cybersecurity-governor/tests:cybersecurity-governor python3 -m pytest \
	  cybersecurity-governor/tests/test_platform_sdk.py \
	  cybersecurity-governor/tests/test_platform_invariant_counters.py \
	  cybersecurity-governor/tests/test_cyber_platforms.py \
	  cybersecurity-governor/tests/test_security_mesh.py -q

cg-chaos-test:
	cd .. && POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5436/cg_chaos \
	  TOXIPROXY_API=http://localhost:8475 \
	  PYTHONPATH=governor-spine-core:cybersecurity-governor/spine/sidecar \
	  python3 -m pytest cybersecurity-governor/tests/chaos/test_toxiproxy_security_ops.py -q

cg-ha-up:
	docker compose -f docker-compose.ha.yml up -d --build --scale cg-sidecar=2 --scale cg-reconciler=2

cg-ha-down:
	docker compose -f docker-compose.ha.yml down

cg-pilot-attestation:
	chmod +x scripts/cg-pilot-attestation.sh scripts/attestation_runner.py
	cd .. && cybersecurity-governor/scripts/cg-pilot-attestation.sh

cg-design-partner-package:
	cd .. && python3 cybersecurity-governor/scripts/generate_design_partner_attestation.py
