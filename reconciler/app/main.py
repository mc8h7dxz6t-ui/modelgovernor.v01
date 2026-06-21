import os
import time

from .sweeper import sweep_expired_reservations


def run() -> None:
    interval_seconds = int(os.getenv("RECONCILER_SWEEP_INTERVAL_SECONDS", "30"))
    while True:
        swept = sweep_expired_reservations()
        print(f"reconciler_sweep_completed swept={swept}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run()
