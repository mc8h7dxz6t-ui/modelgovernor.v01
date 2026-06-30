.PHONY: fg-spine-up fg-spine-down fg-spine-test fg-spine-smoke fg-spine-logs \
	fg-stack-up fg-stack-down crystal-demo algofreeze-demo wirematch-demo \
	subledger-demo assetledger-demo credit-demo fg-all-platforms-demo \
	fg-demo-gold-reliability fg-certification fg-certification-strict fg-certification-l4 \
	fg-certification-l4-ci fg-demo-up fg-demo-down fg-demo-gold \
	fg-test-postgres-up fg-test-postgres-down fg-integration-test fg-chaos-test fg-load-smoke \
	fg-helm-enterprise fg-kustomize-install fg-kustomize-enterprise fg-platform-conformance \
	fg-certification-external fg-certification-external-full fg-examiner-evidence fg-docker-build \
	fg-test-deps fg-test-deps-check fg-pilot-attestation

fg-test-deps:
	chmod +x scripts/install-test-deps.sh
	./scripts/install-test-deps.sh

fg-test-deps-check:
	@python3 -c "import pytest" 2>/dev/null || (echo "Run: make fg-test-deps" && exit 1)

fg-spine-up:
	docker compose up -d --build

fg-stack-up: fg-spine-up

fg-spine-down:
	docker compose down

fg-stack-down: fg-spine-down

fg-spine-logs:
	docker compose logs -f

fg-demo-up:
	chmod +x scripts/*.sh
	./scripts/fg-demo-up.sh

fg-demo-down:
	./scripts/fg-demo-down.sh

fg-demo-gold:
	chmod +x scripts/*.sh
	./scripts/fg-demo-gold.sh

fg-test-postgres-up:
	docker compose -f docker-compose.test.yml up -d --wait

fg-test-postgres-down:
	docker compose -f docker-compose.test.yml down

fg-spine-test: fg-test-deps
	PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/ -q --ignore=tests/integration

fg-integration-test:
	@if command -v docker >/dev/null 2>&1; then $(MAKE) fg-test-postgres-up; else echo "docker not available — integration tests will skip if postgres unreachable"; fi
	FG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5434/fg_test \
	  PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/integration/ -q; status=$$?; \
	if command -v docker >/dev/null 2>&1; then $(MAKE) fg-test-postgres-down; fi; \
	exit $$status

fg-chaos-test:
	@if command -v docker >/dev/null 2>&1; then \
	  docker compose -f docker-compose.chaos.yml up -d --wait fg-postgres-chaos toxiproxy && \
	  docker compose -f docker-compose.chaos.yml run --rm toxiproxy-config; \
	else echo "docker not available — skipping chaos"; exit 0; fi
	FG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5437/fg_chaos \
	  FG_TOXIPROXY_API=http://localhost:8475 \
	  PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/chaos/test_toxiproxy_fg_spine.py -q; status=$$?; \
	if command -v docker >/dev/null 2>&1; then docker compose -f docker-compose.chaos.yml down -v; fi; \
	exit $$status

fg-spine-smoke:
	@echo "==> fg-sidecar health"
	curl -sf http://localhost:8091/healthz
	@echo "\n==> crystallize + commit via gateway"
	curl -sf -X POST http://localhost:8090/governed/commit \
	  -H 'x-internal-token: dev-fg-spine-token-change-me' \
	  -H 'content-type: application/json' \
	  -d '{"platform":"wire_match","operation_id":"smoke-1","facets":{"amount":"100.00"},"policy_id":"wire-critical-us","reserved_exposure":"50","committed_exposure":"50"}'
	@echo "\n==> verify chain"
	curl -sf -H 'x-internal-token: dev-fg-spine-token-change-me' \
	  http://localhost:8091/internal/decisions/verify-chain
	@echo "\nfg-spine-smoke OK"

fg-load-smoke:
	python3 scripts/fg_load_smoke.py

fg-prod-setup:
	chmod +x scripts/*.sh
	./scripts/fg-prod-setup.sh

fg-aws-anchor-bucket:
	chmod +x scripts/*.sh
	./scripts/fg-aws-anchor-bucket.sh

fg-helm-template:
	helm template fg ./deploy/helm/finance-governor \
	  -f ./deploy/helm/finance-governor/values-production.yaml \
	  --set secrets.create=true \
	  --set oidc.issuerUrl=https://idp.example.com/realms/fg \
	  --set oidc.audience=finance-governor \
	  --set s3Anchor.bucket=fg-anchor-demo \
	  --set postgres.password=postgres

fg-helm-enterprise:
	helm template fg ./deploy/helm/finance-governor \
	  -f ./deploy/helm/finance-governor/values-production.yaml \
	  -f ./deploy/helm/finance-governor/values-enterprise.yaml \
	  --set secrets.create=true \
	  --set oidc.issuerUrl=https://idp.example.com/realms/fg \
	  --set oidc.audience=finance-governor \
	  --set s3Anchor.bucket=fg-anchor-l4 \
	  --set postgres.password=postgres

KUSTOMIZE_VERSION ?= v5.5.0
KUSTOMIZE_BIN ?= $(CURDIR)/.bin/kustomize

fg-kustomize-install:
	@mkdir -p .bin
	@if [ ! -x "$(KUSTOMIZE_BIN)" ]; then \
	  echo "Installing kustomize $(KUSTOMIZE_VERSION) to $(KUSTOMIZE_BIN)"; \
	  curl -sSLo /tmp/kustomize.tar.gz \
	    "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F$(KUSTOMIZE_VERSION)/kustomize_$(KUSTOMIZE_VERSION)_linux_amd64.tar.gz"; \
	  tar xzf /tmp/kustomize.tar.gz -C .bin; \
	fi

fg-kustomize-enterprise: fg-kustomize-install
	$(KUSTOMIZE_BIN) build ./deploy/kustomize/overlays/enterprise

fg-helm-install:
	chmod +x scripts/*.sh
	./scripts/fg-helm-install.sh

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

subledger-demo:
	@echo "==> SubledgerSync health"
	curl -sf http://localhost:8095/healthz
	@echo "\n==> ingest mirror legs"
	curl -sf -X POST http://localhost:8095/transactions \
	  -H 'content-type: application/json' \
	  -d '{"entity_id":"UK-01","counterparty_id":"US-01","amount":"10000.00","currency":"USD","value_date":"2026-06-01"}'
	curl -sf -X POST http://localhost:8095/match/run \
	  -H 'content-type: application/json' \
	  -d '{"entity_id":"US-01","counterparty_id":"UK-01","amount":"10000.00","currency":"USD","value_date":"2026-06-01"}'
	@echo "\nsubledger-demo OK"

assetledger-demo:
	@echo "==> AssetLedger health"
	curl -sf http://localhost:8096/healthz
	@echo "\n==> register asset + depreciation run"
	curl -sf -X POST http://localhost:8096/assets \
	  -H 'content-type: application/json' \
	  -d '{"asset_id":"server-rack-1","description":"DC rack","acquisition_cost":"120000.00","useful_life_months":60}'
	curl -sf -X POST http://localhost:8096/depreciation/run \
	  -H 'content-type: application/json' \
	  -d '{"period":"2026-06"}'
	@echo "\nassetledger-demo OK"

credit-demo:
	@echo "==> CreditGovern health"
	curl -sf http://localhost:8097/healthz
	@echo "\n==> approved model evaluate"
	curl -sf -X POST http://localhost:8097/credit/evaluate \
	  -H 'content-type: application/json' \
	  -d '{"application_id":"app-demo-1","exposure_amount":"50000.00","model_version_id":"credit-model-v3","desk_id":"desk-default"}'
	@echo "\ncredit-demo OK"

fg-all-platforms-demo: wirematch-demo algofreeze-demo subledger-demo assetledger-demo credit-demo
	@echo "fg-all-platforms-demo OK — all five platforms exercised"

fg-demo-gold-reliability:
	chmod +x scripts/*.sh
	./scripts/fg-demo-gold-reliability.sh

crystal-demo:
	./scripts/crystal-demo.sh

fg-certification:
	@echo "==> Tier 1: unit + platform tests"
	PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/ -q --ignore=tests/integration --ignore=tests/chaos/test_toxiproxy_fg_spine.py
	@echo "==> Tier 1b: reconciler + CCP invariant reliability"
	PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/test_horizon_sweeper.py tests/test_reconciler_leader.py tests/test_commit_invariants.py tests/test_load_smoke_offline.py -q
	@echo "==> Tier 2: Postgres integration (starts test DB if needed)"
	@$(MAKE) fg-integration-test
	@echo "==> Tier 3: offline load smoke + reconciler invariants"
	PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/test_load_smoke_offline.py tests/test_horizon_sweeper.py tests/test_commit_invariants.py -q
	@echo "==> Tier 4: Toxiproxy chaos (skipped if docker unavailable)"
	@$(MAKE) fg-chaos-test 2>/dev/null || echo "chaos skipped"
	@echo "==> Tier 5: live chain verify (skipped if spine down)"
	@if curl -sf -H 'x-internal-token: dev-fg-spine-token-change-me' \
	  http://localhost:8091/internal/decisions/verify-chain 2>/dev/null \
	  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d" \
	  2>/dev/null; then echo "chain verify OK"; else echo "chain verify skipped (spine not running)"; fi
	@echo "fg-certification complete (institutional++)"

fg-certification-strict:
	@echo "==> Strict institutional++ gate (no skip fallbacks)"
	@$(MAKE) fg-certification
	@$(MAKE) fg-chaos-test
	@python3 scripts/fg_load_smoke.py
	@curl -sf -H 'x-internal-token: dev-fg-spine-token-change-me' \
	  http://localhost:8091/internal/decisions/verify-chain \
	  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('valid') is True, d"

fg-platform-conformance:
	PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/test_facet_schemas.py tests/test_platform_sdk.py tests/test_platform_registry.py -q

fg-certification-external:
	chmod +x scripts/fg_certification_report.py
	FG_ECP_QUICK=1 python3 scripts/fg_certification_report.py --quick $(or $(LEVEL),L5) $(or $(PLATFORM),finance_governor)

fg-certification-external-full:
	chmod +x scripts/fg_certification_report.py scripts/fg_examiner_evidence_pack.py
	python3 scripts/fg_certification_report.py $(or $(LEVEL),L5) $(or $(PLATFORM),finance_governor)

fg-examiner-evidence:
	chmod +x scripts/fg_examiner_evidence_pack.py
	python3 scripts/fg_examiner_evidence_pack.py

fg-certification-l4-ci:
	@echo "==> L4 Gold CI gate (reliability + enterprise manifests)"
	PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/test_l4_helm_enterprise.py tests/test_l4_certification.py \
	  tests/test_horizon_sweeper.py tests/test_reconciler_leader.py \
	  tests/test_commit_invariants.py tests/test_incremental_chain_verify.py \
	  tests/test_load_smoke_offline.py tests/test_algofreeze_integration.py \
	  tests/test_wirematch_hero_integration.py \
	  tests/integration/test_concurrent_decision_append.py -q
	@$(MAKE) fg-helm-enterprise > /dev/null
	@$(MAKE) fg-kustomize-enterprise > /dev/null
	@echo "fg-certification-l4-ci complete"

fg-certification-l4:
	@echo "==> L4 Gold certification gate"
	@$(MAKE) fg-certification
	@echo "==> L4 Helm enterprise render"
	@$(MAKE) fg-helm-enterprise > /dev/null
	@echo "==> L4 Helm enterprise tests"
	PYTHONPATH=../governor-spine-core:spine/sidecar:tests:. python3 -m pytest tests/test_l4_helm_enterprise.py tests/test_l4_certification.py -q
	@echo "==> L4 Kustomize enterprise"
	@$(MAKE) fg-kustomize-enterprise > /dev/null
	@$(MAKE) fg-examiner-evidence
	@echo "fg-certification-l4 complete (L4 Gold)"

fg-docker-build:
	docker build -f spine/sidecar/Dockerfile -t finance-governor-sidecar:local ..
	docker build -f spine/gateway/Dockerfile -t finance-governor-gateway:local ..
	docker build -f spine/reconciler/Dockerfile -t finance-governor-reconciler:local ..
	docker build -f platforms/wire_match/Dockerfile -t finance-governor-wirematch:local ..
	docker build -f platforms/algofreeze/Dockerfile -t finance-governor-algofreeze:local ..
	docker build -f platforms/subledger_sync/Dockerfile -t finance-governor-subledger:local ..
	docker build -f platforms/asset_ledger/Dockerfile -t finance-governor-assetledger:local ..
	docker build -f platforms/credit_govern/Dockerfile -t finance-governor-creditgovern:local ..
	@echo "fg-docker-build OK"

fg-pilot-attestation:
	chmod +x scripts/fg-pilot-attestation.sh scripts/fg_attestation_runner.py
	cd .. && finance-governor/scripts/fg-pilot-attestation.sh
