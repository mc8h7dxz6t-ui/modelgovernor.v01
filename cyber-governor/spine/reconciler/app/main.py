from __future__ import annotations

import logging
import os
import signal
import sys
import time

from .config import get_settings
from .db import get_db_session
from .health_server import start_health_server
from .horizon_sweeper import sweep_expired_horizons
from .leader import reconciler_leader_session

logger = logging.getLogger(__name__)
_shutdown = False
_is_leader = False


def _run_audits(session) -> bool:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sidecar"))
    from app.threat_ops import CrystalOpsInvariantError, assert_threat_ops_invariants
    from app.diagnostic_mode import enter_diagnostic_mode
    from app.metrics import get_counters
    from app.security_ops import RegulatoryOpsInvariantError, assert_security_ops_invariants

    try:
        assert_security_ops_invariants(session)
        assert_threat_ops_invariants(session)
        return True
    except (RegulatoryOpsInvariantError, CrystalOpsInvariantError) as exc:
        get_counters().increment("regulatory_audit_violation_total")
        enter_diagnostic_mode(component="reconciler", reason=str(exc))
        logger.critical("fg spine audit failed: %s", exc)
        return False


def _handle_signal(signum: int, _frame) -> None:
    global _shutdown
    logger.info("signal %s", signum)
    _shutdown = True


def run_loop() -> None:
    global _is_leader
    settings = get_settings()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    start_health_server(port=settings.reconciler_health_port, is_leader=lambda: _is_leader)

    while not _shutdown:
        try:
            with get_db_session() as session:
                with reconciler_leader_session(session) as leader:
                    _is_leader = leader
                    if not leader:
                        time.sleep(settings.reconciler_interval_seconds)
                        continue
                    swept = sweep_expired_horizons(session)
                    if swept:
                        logger.info("swept %d horizon rows", swept)
                    _run_audits(session)
        except Exception:
            logger.exception("reconciler loop error")
        time.sleep(settings.reconciler_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_loop()
