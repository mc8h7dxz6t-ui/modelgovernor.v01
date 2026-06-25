"""Apply Finance Governor SQL migrations to an engine."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _strip_line_comments(sql: str) -> str:
    """Drop `--` line comments so section headers are not mistaken for whole statements."""
    return "\n".join(
        line for line in sql.splitlines() if line.strip() and not line.strip().startswith("--")
    )


def sql_fragments(sql: str) -> list[str]:
    """Split migration SQL into executable statements."""
    return [stmt.strip() for stmt in _strip_line_comments(sql).split(";") if stmt.strip()]


def apply_fg_migrations(engine: Engine, *, migrations_dir: Path | None = None) -> None:
    root = migrations_dir or MIGRATIONS_DIR
    for path in sorted(root.glob("*.sql")):
        with engine.begin() as conn:
            for fragment in sql_fragments(path.read_text()):
                conn.execute(text(fragment))
