from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ReserveRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    wallet_ref: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    estimated_cost: Decimal = Field(ge=Decimal("0"))


class ReserveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ledger_entry_id: str
    reservation_status: str
    amount_reserved: Decimal
    reserved_until: str


class SettleRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    wallet_ref: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    realized_cost: Decimal = Field(ge=Decimal("0"))
    provider_request_id: str | None = None


class SettleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ledger_entry_id: str
    reservation_status: str
    amount_settled: Decimal
    amount_released: Decimal
