.PHONY: demo-up demo-down demo-reset demo-smoke demo-drift-lock demo-status demo-ledger demo-events proof-test load-test

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
