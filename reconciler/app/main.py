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


def _handle_signal(signum: int, _frame) -> None:
    global _shutdown
    logger.info("received signal %s; shutting down reconciler loop", signum)
    _shutdown = True


def run_once() -> int:
    with get_db_session() as session:
        with reconciler_leader_session(session) as is_leader:
            if not is_leader:
                return 0
            swept = sweep_expired_reservations(session)
    print(f"reconciler completed; expired reservations scanned={swept}")
    return swept


def run_daemon() -> None:
    settings = get_settings()
    is_leader_flag = {"value": False}

    def _is_leader() -> bool:
        return is_leader_flag["value"]

    health_server = start_health_server(port=settings.health_port, is_leader=_is_leader)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info(
        "reconciler daemon started interval=%ss health_port=%s",
        settings.sweep_interval_seconds,
        settings.health_port,
    )

    while not _shutdown:
        try:
            with get_db_session() as session:
                with reconciler_leader_session(session) as is_leader:
                    is_leader_flag["value"] = is_leader
                    if is_leader:
                        swept = sweep_expired_reservations(session)
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
