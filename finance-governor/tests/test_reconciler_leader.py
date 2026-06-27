"""Reconciler leader election — advisory lock semantics."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]

from tests.conftest_spine import spine_db  # noqa: F401
from tests.support.reconciler_loader import load_reconciler_module


def test_sqlite_leader_session_always_leader(spine_db):
    reconciler_leader_session = load_reconciler_module("leader").reconciler_leader_session

    factory = sessionmaker(bind=spine_db)
    with factory() as session:
        with reconciler_leader_session(session) as is_leader:
            assert is_leader is True
