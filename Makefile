.PHONY: demo-up demo-down demo-reset demo-smoke demo-drift-lock demo-status demo-ledger demo-events \
	demo-gold-up demo-gold demo-gold-reliability demo-gold-down demo-gold-reset demo-gold-diagnose \
	demo-all-platforms demo-all-platforms-live demo-all-platforms-manifests demo-all-platforms-proof \
	demo-prereqs demo-prereqs-install proof-test load-test \
	fg-spine-up fg-stack-up fg-spine-down fg-stack-down fg-spine-test fg-spine-smoke \
	crystal-demo algofreeze-demo wirematch-demo \
	cg-spine-up cg-stack-up cg-spine-down cg-stack-down cg-spine-test cg-spine-smoke \
	threat-crystal-demo identity-gate-demo egress-lock-demo witness-bridge-demo \
	cg-security-demo lineage-ingest-demo cg-bootstrap cg-prod-bootstrap

demo-prereqs:
	./scripts/install-demo-prereqs.sh --check-only

demo-prereqs-install:
	./scripts/install-demo-prereqs.sh --install

demo-gold-up:
	./scripts/demo-gold-up.sh

demo-gold:
	./scripts/demo-gold.sh

demo-gold-reliability:
	./scripts/demo-gold-reliability-only.sh

demo-gold-down:
	./scripts/demo-gold-down.sh

demo-gold-reset:
	./scripts/demo-gold-reset.sh

demo-gold-diagnose:
	./scripts/demo-gold-diagnose.sh

demo-up:
	./scripts/demo-up.sh

demo-down:
	./scripts/demo-down.sh

demo-reset:
	./scripts/demo-reset.sh

demo-smoke:
	./scripts/demo-smoke.sh

demo-drift-lock:
	./scripts/demo-drift-lock.sh

demo-status:
	./scripts/demo-status.sh

demo-ledger:
	./scripts/demo-ledger.sh

demo-events:
	./scripts/demo-events.sh

proof-test:
	pytest -q tests/integration/test_ledger_hardening.py tests/integration/test_postgres_vigorous.py

load-test:
	LOAD_WORKERS=12 LOAD_OPS_PER_WORKER=8 python scripts/generate_invariant_report.py

# Finance Governor spine (sibling to ModelGovernor)
fg-spine-up:
	$(MAKE) -C finance-governor fg-spine-up

fg-stack-up:
	$(MAKE) -C finance-governor fg-stack-up

fg-spine-down:
	$(MAKE) -C finance-governor fg-spine-down

fg-stack-down:
	$(MAKE) -C finance-governor fg-stack-down

fg-spine-test:
	$(MAKE) -C finance-governor fg-spine-test

fg-spine-smoke:
	$(MAKE) -C finance-governor fg-spine-smoke

crystal-demo:
	$(MAKE) -C finance-governor crystal-demo

algofreeze-demo:
	$(MAKE) -C finance-governor algofreeze-demo

wirematch-demo:
	$(MAKE) -C finance-governor wirematch-demo

cg-spine-up:
	$(MAKE) -C cyber-governor cg-spine-up

cg-stack-up:
	$(MAKE) -C cyber-governor cg-stack-up

cg-spine-down:
	$(MAKE) -C cyber-governor cg-spine-down

cg-stack-down:
	$(MAKE) -C cyber-governor cg-stack-down

cg-spine-test:
	$(MAKE) -C cyber-governor cg-spine-test

cg-spine-smoke:
	$(MAKE) -C cyber-governor cg-spine-smoke

threat-crystal-demo:
	$(MAKE) -C cyber-governor threat-crystal-demo

identity-gate-demo:
	$(MAKE) -C cyber-governor identity-gate-demo

egress-lock-demo:
	$(MAKE) -C cyber-governor egress-lock-demo

witness-bridge-demo:
	$(MAKE) -C cyber-governor witness-bridge-demo

cg-security-demo:
	$(MAKE) -C cyber-governor cg-security-demo

lineage-ingest-demo:
	$(MAKE) -C cyber-governor lineage-ingest-demo

cg-postgres-test:
	$(MAKE) -C cyber-governor cg-postgres-test

cg-proof-test:
	$(MAKE) -C cyber-governor cg-proof-test

cg-deploy-dry-run:
	$(MAKE) -C cyber-governor cg-deploy-dry-run

cg-bootstrap:
	$(MAKE) -C cyber-governor cg-bootstrap

cg-prod-bootstrap:
	$(MAKE) -C cyber-governor cg-prod-bootstrap
