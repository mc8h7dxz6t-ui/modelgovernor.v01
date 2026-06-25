"""Apply Finance Governor SQL migrations to an engine."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def apply_fg_migrations(engine: Engine, *, migrations_dir: Path | None = None) -> None:
    root = migrations_dir or MIGRATIONS_DIR
    for path in sorted(root.glob("*.sql")):
        sql = path.read_text()
        with engine.begin() as conn:
            for stmt in sql.split(";"):
                fragment = stmt.strip()
                if not fragment or fragment.startswith("--"):
                    continue
                conn.execute(text(fragment))
