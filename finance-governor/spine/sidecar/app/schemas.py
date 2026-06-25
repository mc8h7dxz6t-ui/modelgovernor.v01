from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class CrystallizeRequest(BaseModel):
    platform: str
    operation_id: str
    account_id: str = "desk-default"
    risk_tier: str = "high"
    facets: dict[str, Any] = Field(default_factory=dict)
    policy_id: str | None = None
    reserved_exposure: Decimal = Decimal("0")
    parent_crystal_id: str | None = None


class CrystallizeResponse(BaseModel):
    crystal_id: str
    operation_id: str
    status: str
    horizon_expires_at: datetime


class CommitRequest(BaseModel):
    crystal_id: str
    facets: dict[str, Any]
    committed_exposure: Decimal = Decimal("0")
    outcome: str = "committed"
    late_authority: bool = False


class CommitResponse(BaseModel):
    operation_id: str
    crystal_id: str
    status: str


class HealthResponse(BaseModel):
    status: str
    details: dict[str, Any] | None = None
