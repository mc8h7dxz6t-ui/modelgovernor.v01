"""ZK claim commitment store — Postgres with in-memory fallback."""
from __future__ import annotations

import json
from typing import Any

from platforms.zk_claim_audit.proof_gate import ClaimCommitment

from .db import platform_connection, platform_db_enabled


class MemoryCommitmentStore:
    def __init__(self) -> None:
        self._data: dict[str, ClaimCommitment] = {}
        self._facts: dict[str, dict[str, Any]] = {}

    def get(self, claim_id: str) -> ClaimCommitment | None:
        return self._data.get(claim_id)

    def get_facts(self, claim_id: str) -> dict[str, Any]:
        return self._facts.get(claim_id, {})

    def save(self, claim_id: str, commitment: ClaimCommitment, private_facts: dict[str, Any]) -> None:
        self._data[claim_id] = commitment
        self._facts[claim_id] = private_facts

    def clear(self) -> None:
        self._data.clear()
        self._facts.clear()


class PostgresCommitmentStore:
    def get(self, claim_id: str) -> ClaimCommitment | None:
        with platform_connection() as conn:
            if conn is None:
                return None
            row = conn.execute(
                """
                SELECT commitment_id, commitment_hash, salt, fact_count
                FROM claim_commitments WHERE claim_id = %s
                """,
                (claim_id,),
            ).fetchone()
            if row is None:
                return None
            return ClaimCommitment(
                commitment_id=row[0],
                claim_id=claim_id,
                commitment_hash=row[1],
                salt=row[2],
                fact_count=row[3],
            )

    def get_facts(self, claim_id: str) -> dict[str, Any]:
        with platform_connection() as conn:
            if conn is None:
                return {}
            row = conn.execute(
                "SELECT private_facts FROM claim_commitments WHERE claim_id = %s",
                (claim_id,),
            ).fetchone()
            if row is None:
                return {}
            facts = row[0]
            if isinstance(facts, str):
                return json.loads(facts)
            return dict(facts or {})

    def save(self, claim_id: str, commitment: ClaimCommitment, private_facts: dict[str, Any]) -> None:
        with platform_connection() as conn:
            if conn is None:
                raise RuntimeError("postgres commitment store unavailable")
            conn.execute(
                """
                INSERT INTO claim_commitments (
                    claim_id, commitment_id, commitment_hash, salt, fact_count, private_facts
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (claim_id) DO UPDATE SET
                    commitment_id = EXCLUDED.commitment_id,
                    commitment_hash = EXCLUDED.commitment_hash,
                    salt = EXCLUDED.salt,
                    fact_count = EXCLUDED.fact_count,
                    private_facts = EXCLUDED.private_facts,
                    sealed_at = CURRENT_TIMESTAMP
                """,
                (
                    claim_id,
                    commitment.commitment_id,
                    commitment.commitment_hash,
                    commitment.salt,
                    commitment.fact_count,
                    json.dumps(private_facts),
                ),
            )
            conn.commit()

    def clear(self) -> None:
        with platform_connection() as conn:
            if conn is None:
                return
            conn.execute("DELETE FROM claim_commitments")
            conn.commit()


_STORE: MemoryCommitmentStore | PostgresCommitmentStore | None = None


def get_commitment_store() -> MemoryCommitmentStore | PostgresCommitmentStore:
    global _STORE
    if _STORE is None:
        _STORE = PostgresCommitmentStore() if platform_db_enabled() else MemoryCommitmentStore()
    return _STORE


def reset_commitment_stores() -> None:
    global _STORE
    _STORE = None
