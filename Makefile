.PHONY: demo-up demo-down demo-reset demo-smoke demo-drift-lock demo-status demo-ledger demo-events \
	demo-gold-up demo-gold demo-gold-reliability demo-gold-down demo-gold-reset demo-gold-diagnose \
	demo-all demo-all-platforms demo-all-platforms-live demo-all-platforms-manifests demo-all-platforms-proof \
	demo-prereqs demo-prereqs-install proof-test load-test \
	fg-spine-up fg-stack-up fg-spine-down fg-stack-down fg-spine-test fg-spine-smoke \
	crystal-demo algofreeze-demo wirematch-demo fg-certification \
	fg-demo-up fg-demo-down fg-demo-gold fg-integration-test fg-load-smoke \
	fg-prod-setup fg-aws-anchor-bucket fg-helm-template fg-helm-install fg-examiner-evidence \
	ig-spine-up ig-stack-up ig-spine-down ig-stack-down ig-spine-test ig-spine-smoke \
	claim-gate-demo ig-demo ig-certification ig-certification-strict ig-certification-l4 ig-certification-l4-ci \
	ig-helm-enterprise ig-platform-conformance ig-load-test ig-ha-up ig-pilot-attestation \
	ig-cluster-attestation ig-rail-smoke ig-design-partner-package ig-claim-gate-load \
	ig-full-rehearsal ig-embedded-rehearsal ig-examiner-evidence \
	cg-spine-up cg-stack-up cg-spine-down cg-stack-down cg-spine-test cg-spine-smoke \
	egress-govern-demo cg-demo cg-certification cg-certification-strict cg-certification-l4 cg-certification-l4-ci \
	cg-helm-enterprise cg-platform-conformance cg-load-test cg-examiner-evidence

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

demo-all:
	./scripts/demo-all.sh

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

fg-certification:
	$(MAKE) -C finance-governor fg-certification

fg-demo-up:
	$(MAKE) -C finance-governor fg-demo-up

fg-demo-down:
	$(MAKE) -C finance-governor fg-demo-down

fg-demo-gold:
	$(MAKE) -C finance-governor fg-demo-gold

fg-integration-test:
	$(MAKE) -C finance-governor fg-integration-test

fg-load-smoke:
	$(MAKE) -C finance-governor fg-load-smoke

fg-prod-setup:
	$(MAKE) -C finance-governor fg-prod-setup

fg-aws-anchor-bucket:
	$(MAKE) -C finance-governor fg-aws-anchor-bucket

fg-helm-template:
	$(MAKE) -C finance-governor fg-helm-template

fg-helm-install:
	$(MAKE) -C finance-governor fg-helm-install

fg-examiner-evidence:
	$(MAKE) -C finance-governor fg-examiner-evidence

# Insurance Governor spine (sibling to ModelGovernor / Finance Governor)
ig-spine-up:
	$(MAKE) -C insurance-governor ig-spine-up

ig-stack-up:
	$(MAKE) -C insurance-governor ig-stack-up

ig-spine-down:
	$(MAKE) -C insurance-governor ig-spine-down

ig-stack-down:
	$(MAKE) -C insurance-governor ig-stack-down

ig-spine-test:
	$(MAKE) -C insurance-governor ig-spine-test

ig-spine-smoke:
	$(MAKE) -C insurance-governor ig-spine-smoke

claim-gate-demo:
	$(MAKE) -C insurance-governor claim-gate-demo

ig-demo:
	$(MAKE) -C insurance-governor ig-demo

ig-certification:
	$(MAKE) -C insurance-governor ig-certification

ig-certification-strict:
	$(MAKE) -C insurance-governor ig-certification-strict

ig-certification-l4:
	$(MAKE) -C insurance-governor ig-certification-l4

ig-certification-l4-ci:
	$(MAKE) -C insurance-governor ig-certification-l4-ci

ig-helm-enterprise:
	$(MAKE) -C insurance-governor ig-helm-enterprise

ig-platform-conformance:
	$(MAKE) -C insurance-governor ig-platform-conformance

ig-examiner-evidence:
	$(MAKE) -C insurance-governor ig-examiner-evidence

ig-load-test:
	$(MAKE) -C insurance-governor ig-load-test

ig-ha-up:
	$(MAKE) -C insurance-governor ig-ha-up

ig-pilot-attestation:
	$(MAKE) -C insurance-governor ig-pilot-attestation

ig-cluster-attestation:
	$(MAKE) -C insurance-governor ig-cluster-attestation

ig-rail-smoke:
	$(MAKE) -C insurance-governor ig-rail-smoke

ig-design-partner-package:
	$(MAKE) -C insurance-governor ig-design-partner-package

ig-claim-gate-load:
	$(MAKE) -C insurance-governor ig-claim-gate-load

ig-full-rehearsal:
	$(MAKE) -C insurance-governor ig-full-rehearsal

ig-embedded-rehearsal:
	$(MAKE) -C insurance-governor ig-embedded-rehearsal

cg-spine-up:
	$(MAKE) -C cybersecurity-governor cg-spine-up

cg-stack-up:
	$(MAKE) -C cybersecurity-governor cg-stack-up

cg-spine-down:
	$(MAKE) -C cybersecurity-governor cg-spine-down

cg-stack-down:
	$(MAKE) -C cybersecurity-governor cg-stack-down

cg-spine-test:
	$(MAKE) -C cybersecurity-governor cg-spine-test

cg-spine-smoke:
	$(MAKE) -C cybersecurity-governor cg-spine-smoke

egress-govern-demo:
	$(MAKE) -C cybersecurity-governor egress-govern-demo

cg-demo:
	$(MAKE) -C cybersecurity-governor cg-demo

cg-certification:
	$(MAKE) -C cybersecurity-governor cg-certification

cg-certification-strict:
	$(MAKE) -C cybersecurity-governor cg-certification-strict

cg-certification-l4:
	$(MAKE) -C cybersecurity-governor cg-certification-l4

cg-certification-l4-ci:
	$(MAKE) -C cybersecurity-governor cg-certification-l4-ci

cg-helm-enterprise:
	$(MAKE) -C cybersecurity-governor cg-helm-enterprise

cg-platform-conformance:
	$(MAKE) -C cybersecurity-governor cg-platform-conformance

cg-examiner-evidence:
	$(MAKE) -C cybersecurity-governor cg-examiner-evidence

cg-load-test:
	$(MAKE) -C cybersecurity-governor cg-load-test

demo-all-platforms:
	./scripts/demo-all-platforms.sh

demo-all-platforms-live:
	./scripts/demo-all-platforms.sh --live-only

demo-all-platforms-manifests:
	./scripts/demo-all-platforms.sh --manifests-only

demo-all-platforms-proof:
	./scripts/demo-all-platforms.sh --with-proof
