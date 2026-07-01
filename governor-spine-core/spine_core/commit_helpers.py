"""Shared crystallize/commit helpers for FG/IG/CG CCP paths."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def money_param(value: Decimal, quantize_fn: Callable[[Decimal], Decimal]) -> str | Decimal:
    return str(quantize_fn(value))


def ts_param(session: Session, value: datetime) -> str | datetime:
    if session.bind.dialect.name == "sqlite":
        return value.isoformat()
    return value
