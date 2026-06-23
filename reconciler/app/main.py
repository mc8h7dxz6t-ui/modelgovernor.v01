from __future__ import annotations

import logging
import os
import signal
import sys
import time

from .config import get_settings
from .db import get_db_session
from .health_server import start_health_server
from .leader import reconciler_leader_session
from .sweeper import sweep_expired_reservations

logger = logging.getLogger(__name__)
_shutdown = False


def _run_finance_audit(session) -> bool:
    from sidecar.app.diagnostic_mode import enter_diagnostic_mode
    from sidecar.app.finance_ops import FinanceOpsInvariantError, assert_finance_ops_invariants
    from sidecar.app.metrics import get_counters

    try:
        assert_finance_ops_invariants(session)
        return True
    except FinanceOpsInvariantError as exc:
        get_counters().increment("finance_audit_violation_total")
        enter_diagnostic_mode(component="reconciler", reason=str(exc))
        logger.critical("post-sweep finance invariant audit failed — diagnostic mode engaged")
        return False


def _handle_signal(signum: int, _frame) -> None:
    global _shutdown
    logger.info("received signal %s; shutting down reconciler loop", signum)
    _shutdown = True


def run_once() -> int:
    from sidecar.app.diagnostic_mode import is_diagnostic_mode

    if is_diagnostic_mode():
        logger.warning("diagnostic mode active; reconciler once-mode sweep skipped")
        return 0
    with get_db_session() as session:
        with reconciler_leader_session(session) as is_leader:
            if not is_leader:
                return 0
            swept = sweep_expired_reservations(session)
            _run_finance_audit(session)
    print(f"reconciler completed; expired reservations scanned={swept}")
    return swept


def run_daemon() -> None:
    from sidecar.app.diagnostic_mode import diagnostic_snapshot, is_diagnostic_mode

    settings = get_settings()
    is_leader_flag = {"value": False}

    def _is_leader() -> bool:
        return is_leader_flag["value"]

    def _health_payload() -> dict:
        payload = {"leader": is_leader_flag["value"]}
        payload.update(diagnostic_snapshot())
        return payload

    health_server = start_health_server(
        port=settings.health_port,
        is_leader=_is_leader,
        extra_status=_health_payload,
    )
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info(
        "reconciler daemon started interval=%ss health_port=%s",
        settings.sweep_interval_seconds,
        settings.health_port,
    )

    while not _shutdown:
        try:
            if is_diagnostic_mode():
                is_leader_flag["value"] = False
                logger.warning("diagnostic mode active; automated sweeps halted")
            else:
                with get_db_session() as session:
                    with reconciler_leader_session(session) as is_leader:
                        is_leader_flag["value"] = is_leader
                        if is_leader:
                            swept = sweep_expired_reservations(session)
                            _run_finance_audit(session)
                            logger.info("reconciler sweep complete swept=%s", swept)
        except Exception:
            logger.exception("reconciler sweep failed")
        time.sleep(settings.sweep_interval_seconds)

    health_server.shutdown()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    mode = os.getenv("RECONCILER_MODE", "once").lower()
    if mode == "daemon":
        run_daemon()
    else:
        swept = run_once()
        if swept < 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
