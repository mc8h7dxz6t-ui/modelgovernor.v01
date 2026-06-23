"""Apply SQL migrations in Postgres tests (dollar-quotes + line comments)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine


def iter_pg_sql_statements(sql: str) -> list[str]:
    """Split SQL on semicolons outside comments and dollar-quoted blocks."""
    sql = _strip_sql_line_comments(sql)
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    in_dollar = False
    dollar_tag = ""

    while i < n:
        if not in_dollar and sql[i] == "$":
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < n and sql[j] == "$":
                dollar_tag = sql[i : j + 1]
                in_dollar = True
                buf.append(dollar_tag)
                i = j + 1
                continue
        if in_dollar and sql.startswith(dollar_tag, i):
            buf.append(dollar_tag)
            i += len(dollar_tag)
            in_dollar = False
            dollar_tag = ""
            continue
        if not in_dollar and sql[i] == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(sql[i])
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _strip_sql_line_comments(sql: str) -> str:
    lines: list[str] = []
    for line in sql.splitlines():
        cleaned: list[str] = []
        in_single = False
        in_double = False
        i = 0
        while i < len(line):
            ch = line[i]
            if (
                not in_single
                and not in_double
                and ch == "-"
                and i + 1 < len(line)
                and line[i + 1] == "-"
            ):
                break
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            cleaned.append(ch)
            i += 1
        lines.append("".join(cleaned))
    return "\n".join(lines)


def apply_migrations_to_engine(engine: Engine, migrations_dir: Path, filenames: list[str]) -> None:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for filename in filenames:
            sql = (migrations_dir / filename).read_text(encoding="utf-8")
            for statement in iter_pg_sql_statements(sql):
                conn.execute(text(statement))
