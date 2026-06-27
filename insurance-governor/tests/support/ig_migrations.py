"""Apply Insurance Governor SQL migrations to an engine."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _strip_line_comments(sql: str) -> str:
    return "\n".join(
        line for line in sql.splitlines() if line.strip() and not line.strip().startswith("--")
    )


def sql_fragments(sql: str) -> list[str]:
    return [stmt.strip() for stmt in _strip_line_comments(sql).split(";") if stmt.strip()]


def _schema_bootstrapped(engine: Engine) -> bool:
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if dialect == "sqlite":
            row = conn.execute(
                text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'reserve_ledgers'")
            ).first()
        else:
            row = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'reserve_ledgers'"
                )
            ).first()
    return row is not None


def apply_ig_migrations(
    engine: Engine, *, migrations_dir: Path | None = None, force: bool = False
) -> None:
    if not force and _schema_bootstrapped(engine):
        return
    root = migrations_dir or MIGRATIONS_DIR
    for path in sorted(root.glob("*.sql")):
        with engine.begin() as conn:
            for fragment in sql_fragments(path.read_text()):
                conn.exec_driver_sql(fragment)
