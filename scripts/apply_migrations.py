#!/usr/bin/env python3
"""Apply SQL migrations from migrations/ directory."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    migrations_dir = Path(os.environ.get("MIGRATIONS_DIR", Path(__file__).resolve().parents[1] / "migrations"))
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        raise SystemExit(f"no migrations in {migrations_dir}")

    dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            for migration_file in files:
                sql = migration_file.read_text(encoding="utf-8")
                for statement in _iter_sql_statements(sql):
                    if statement.strip():
                        cur.execute(statement)
    print(f"applied {len(files)} migration files from {migrations_dir}")
    return 0


def _iter_sql_statements(sql: str):
    buffer: list[str] = []
    for line in sql.splitlines():
        buffer.append(line)
        candidate = "\n".join(buffer).strip()
        if candidate and sqlite3.complete_statement(candidate):
            yield candidate
            buffer = []
    candidate = "\n".join(buffer).strip()
    if candidate:
        yield candidate


if __name__ == "__main__":
    raise SystemExit(main())
