import json
import logging
import sys

from app.db import get_db_session
from app.sweeper import sweep_expired_reservations

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    with get_db_session() as session:
        swept = sweep_expired_reservations(session)
        logger.info(
            json.dumps(
                {
                    "event": "reconciler_sweep_complete",
                    "swept_count": swept,
                }
            )
        )


if __name__ == "__main__":
    main()
