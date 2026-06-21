from contextlib import contextmanager

import psycopg

from .config import settings


@contextmanager
def get_db_connection():
    conn = psycopg.connect(settings.database_url)
    try:
        yield conn
    finally:
        conn.close()
