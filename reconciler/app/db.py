from contextlib import contextmanager
import os

import psycopg


@contextmanager
def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    conn = psycopg.connect(database_url)
    try:
        yield conn
    finally:
        conn.close()
