import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.auth import require_internal_auth
from app.db import get_db_session
from app.policy import PolicyDecisionError, quantize_money, validate_settle_request
from app.schemas import SettleRequest, SettleResponse

router = APIRouter(tags=["settle"])


@router.post("/settle", response_model=SettleResponse, dependencies=[Depends(require_internal_auth)])
def settle(request: SettleRequest) -> SettleResponse:
    try:
        validate_settle_request(request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    actual_amount = quantize_money(request.actual_cost)

    with get_db_session() as session:
        ledger_row = session.execute(
            text(
                """
                SELECT idempotency_key, user_id, reserved_amount, actual_amount, status, provider_request_id, expired_at
                FROM escrow_ledger
                WHERE idempotency_key = :idempotency_key
                FOR UPDATE
                """
            ),
            {"idempotency_key": request.idempotency_key},
        ).mappings().first()

        if ledger_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reservation not found")

        if ledger_row["status"] == "SETTLED":
            persisted_actual_amount = quantize_money(ledger_row["actual_amount"])
            persisted_provider_request_id = ledger_row["provider_request_id"]
            if persisted_actual_amount != actual_amount or persisted_provider_request_id != request.provider_request_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_key already settled with different parameters",
                )
            return SettleResponse(
                idempotency_key=ledger_row["idempotency_key"],
                status="SETTLED",
                actual_amount=persisted_actual_amount,
            )

        if ledger_row["status"] == "EXPIRED" or ledger_row["expired_at"] is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expired reservations cannot be settled")

        if ledger_row["status"] != "RESERVED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="reservation is not eligible for settlement")

        wallet_row = session.execute(
            text(
                """
                SELECT user_id, balance, active
                FROM user_wallets
                WHERE user_id = :user_id
                FOR UPDATE
                """
            ),
            {"user_id": ledger_row["user_id"]},
        ).mappings().first()

        if wallet_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallet not found")

        if not wallet_row["active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="wallet is inactive")

        reserved_amount = quantize_money(ledger_row["reserved_amount"])
        refund_amount = quantize_money(max(reserved_amount - actual_amount, 0))
        drift_amount = quantize_money(actual_amount - reserved_amount)

        session.execute(
            text(
                """
                UPDATE escrow_ledger
                SET actual_amount = :actual_amount,
                    status = 'SETTLED',
                    provider_request_id = :provider_request_id,
                    settled_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE idempotency_key = :idempotency_key
                """
            ),
            {
                "actual_amount": actual_amount,
                "provider_request_id": request.provider_request_id,
                "idempotency_key": request.idempotency_key,
            },
        )

        if refund_amount > 0:
            session.execute(
                text(
                    """
                    UPDATE user_wallets
                    SET balance = balance + :refund_amount,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                    """
                ),
                {"refund_amount": refund_amount, "user_id": ledger_row["user_id"]},
            )

        session.execute(
            text(
                """
                INSERT INTO ledger_events (
                    idempotency_key,
                    user_id,
                    event_type,
                    amount_delta,
                    metadata
                )
                VALUES (
                    :idempotency_key,
                    :user_id,
                    'SETTLED_FINAL',
                    :amount_delta,
                    CAST(:metadata AS JSONB)
                )
                """
            ),
            {
                "idempotency_key": request.idempotency_key,
                "user_id": ledger_row["user_id"],
                "amount_delta": refund_amount,
                "metadata": json.dumps(
                    {"provider_request_id": request.provider_request_id, "actual_amount": str(actual_amount)}
                ),
            },
        )

        if drift_amount != 0:
            session.execute(
                text(
                    """
                    INSERT INTO ledger_events (
                        idempotency_key,
                        user_id,
                        event_type,
                        amount_delta,
                        metadata
                    )
                    VALUES (
                        :idempotency_key,
                        :user_id,
                        'SETTLEMENT_DRIFT',
                        :amount_delta,
                        CAST(:metadata AS JSONB)
                    )
                    """
                ),
                {
                    "idempotency_key": request.idempotency_key,
                    "user_id": ledger_row["user_id"],
                    "amount_delta": drift_amount,
                    "metadata": json.dumps(
                        {"reserved_amount": str(reserved_amount), "actual_amount": str(actual_amount)}
                    ),
                },
            )

        session.commit()

    return SettleResponse(
        idempotency_key=request.idempotency_key,
        status="SETTLED",
        actual_amount=actual_amount,
    )
