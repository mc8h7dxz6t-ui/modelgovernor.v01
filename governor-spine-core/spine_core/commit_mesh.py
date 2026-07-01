"""Crystal mesh block evaluation — shared across FG/IG/CG commit paths."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def mesh_block_reason(session: Session, platform: str, facets: dict[str, Any]) -> str | None:
    """Return a human-readable block reason when mesh rules forbid commit, else None."""
    _ = facets
    rows = session.execute(
        text(
            """
            SELECT parent_platform, parent_facet_key, parent_facet_value
            FROM crystal_mesh_rules
            WHERE child_platform = :platform AND block_commit = TRUE AND enabled = TRUE
            """
        ),
        {"platform": platform},
    ).mappings().all()
    for rule in rows:
        parent = session.execute(
            text(
                """
                SELECT facets FROM governance_crystals
                WHERE platform = :pp AND terminal_state IS NULL
                ORDER BY crystallized_at DESC LIMIT 1
                """
            ),
            {"pp": rule["parent_platform"]},
        ).first()
        if not parent:
            continue
        pf = parent[0] if isinstance(parent[0], dict) else json.loads(parent[0])
        if pf.get(rule["parent_facet_key"]) == rule["parent_facet_value"]:
            return (
                f"mesh block: {rule['parent_platform']}."
                f"{rule['parent_facet_key']}={rule['parent_facet_value']}"
            )
    return None
