from app.db import get_db_session
from app.sweeper import sweep_expired_reservations


def main() -> None:
    with get_db_session() as session:
        swept = sweep_expired_reservations(session)
        print(f"reconciler completed; expired reservations scanned={swept}")


if __name__ == "__main__":
    main()
