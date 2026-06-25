.PHONY: fg-spine-up fg-spine-down fg-spine-test fg-spine-smoke fg-spine-logs \
	fg-stack-up fg-stack-down crystal-demo algofreeze-demo wirematch-demo \
	subledger-demo assetledger-demo creditgovern-demo fg-certification fg-mesh-demo \
	fg-postgres-test-up fg-postgres-test-down fg-chaos-up fg-chaos-test fg-l4-certification

fg-spine-up:
	docker compose up -d --build

fg-stack-up: fg-spine-up

fg-spine-down:
	docker compose down

fg-stack-down: fg-spine-down

fg-spine-logs:
	docker compose logs -f

fg-spine-test:
	python3 -m pytest tests/ -q

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
	cd .. && PYTHONPATH=finance-governor python3 -c "\
from decimal import Decimal; \
from platforms.subledger_sync.match_engine import IcTransaction, MatchEngine; \
from platforms.subledger_sync.fx_snapshot import capture_fx_snapshot; \
e=MatchEngine(); \
fx=capture_fx_snapshot(base_currency='GBP', quote_currency='USD', rate=Decimal('1.27')); \
r=e.match_with_fx(IcTransaction('a','UK','US',Decimal('-1000'),'GBP'), IcTransaction('b','US','UK',Decimal('1000'),'GBP'), fx); \
print('MATCHED', r.matched, r.fx_snapshot_hash[:16])"

assetledger-demo:
	cd .. && PYTHONPATH=finance-governor python3 -c "\
from decimal import Decimal; \
from platforms.asset_ledger.asset_registry import Asset, AssetRegistry; \
from platforms.asset_ledger.depreciation_engine import DepreciationEngine; \
from platforms.asset_ledger.reg_table_sync import RegTableSync; \
r=AssetRegistry(); r.register(Asset('demo', Decimal('100000'))); \
e=DepreciationEngine(r, RegTableSync()); \
c=e.run_period_charge('demo','2026-06','UK:hmrc'); \
print('CHARGE', c.charge, 'VERSION', c.reg_table_version)"

creditgovern-demo:
	cd .. && PYTHONPATH=finance-governor python3 -c "\
from decimal import Decimal; \
from platforms.credit_govern.exposure_ledger import ExposureLedger; \
from platforms.credit_govern.score_gate import PolicyRegistry, ScoreGate; \
l=ExposureLedger(); l.ensure_desk('d', Decimal('500000')); \
g=ScoreGate(l, PolicyRegistry('credit-v3.2.1', Decimal('25000'))); \
print(g.governed_decision(application_id='demo', desk_id='d', exposure_amount=Decimal('5000'), model_version='credit-v3.2.1', feature_snapshot_hash='low-risk-hash'))"

fg-mesh-demo:
	cd .. && PYTHONPATH=finance-governor python3 -c "\
from decimal import Decimal; \
from platforms.common.mesh_guard import get_mesh_guard; \
from platforms.wire_match.execution_gate import evaluate_and_gate; \
from platforms.wire_match.semantic_matcher import GoldenRecord; \
g=GoldenRecord('Revlon Lenders Group','US12REV001',Decimal('7800000')); \
get_mesh_guard().set_algo_frozen('VERSION_MISMATCH'); \
d=evaluate_and_gate(wire_id='m', beneficiary_name='Revlon Lenders Group', beneficiary_account='US12REV001', amount=Decimal('7800000'), golden=g); \
print('MESH_BLOCK', d.decision, d.reason)"

fg-certification:
	cd .. && python3 finance-governor/scripts/generate_fg_certification.py

fg-l4-certification:
	cd .. && FG_CERTIFICATION_LEVEL=L4_GOLD python3 finance-governor/scripts/generate_fg_certification.py

fg-postgres-test-up:
	docker compose -f docker-compose.fg-test.yml up -d --wait

fg-postgres-test-down:
	docker compose -f docker-compose.fg-test.yml down

fg-chaos-up:
	docker compose -f docker-compose.fg-chaos.yml up -d --wait fg-postgres-chaos toxiproxy
	docker compose -f docker-compose.fg-chaos.yml run --rm fg-toxiproxy-config

fg-chaos-test:
	cd .. && FG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5437/fg_chaos \
	  FG_TOXIPROXY_API=http://localhost:8475 \
	  PYTHONPATH=finance-governor/spine/sidecar:finance-governor \
	  python3 -m pytest finance-governor/tests/chaos/ -q

crystal-demo:
	./scripts/crystal-demo.sh
