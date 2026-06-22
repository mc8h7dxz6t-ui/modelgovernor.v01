from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth import require_internal_auth
from app.config import get_settings
from app.db import get_db_session
from app.policy import (
    PolicyDecisionError,
    calculate_reserve_amount,
    quantize_money,
    validate_reserve_request,
)
from app.schemas import ReserveRequest, ReserveResponse

router = APIRouter(tags=["reserve"])


@router.post("/reserve", response_model=ReserveResponse, dependencies=[Depends(require_internal_auth)])
def reserve(request: ReserveRequest) -> ReserveResponse:
    try:
        validate_reserve_request(request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    settings = get_settings()
    reserve_amount = calculate_reserve_amount(request.estimated_cost)

    with get_db_session() as session:
        existing = session.execute(
            text(
                """
                SELECT idempotency_key, user_id, trace_id, model, reserved_amount, status, expires_at
                FROM escrow_ledger
                WHERE idempotency_key = :idempotency_key
                """
            ),
            {"idempotency_key": request.idempotency_key},
        ).mappings().first()

        if existing is not None:
            if (
                existing["user_id"] != request.user_id
                or existing["trace_id"] != request.trace_id
                or existing["model"] != request.model
                or quantize_money(existing["reserved_amount"]) != reserve_amount
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_key already exists with different reserve parameters",
                )

            expires_in_seconds = max(
                0,
                int((existing["expires_at"] - existing["expires_at"].tzinfo.fromutc(existing["expires_at"].replace(tzinfo=existing["expires_at"].tzinfo))).total_seconds())
                if existing["expires_at"].tzinfo is not None
                else settings.reserve_ttl_seconds,
            )
            return ReserveResponse(
                idempotency_key=existing["idempotency_key"],
                status=existing["status"],
                reserved_amount=quantize_money(existing["reserved_amount"]),
                expires_in_seconds=expires_in_seconds or settings.reserve_ttl_seconds,
            )

        model_policy = session.execute(
            text(
                """
                SELECT enabled, max_cost_per_request
                FROM model_policy_registry
                WHERE model_name = :model_name
                """
            ),
            {"model_name": request.model},
        ).mappings().first()

        if model_policy is None or not model_policy["enabled"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model is not enabled")

        if reserve_amount > quantize_money(model_policy["max_cost_per_request"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reserve exceeds model policy maximum")

        wallet = session.execute(
            text(
                """
                SELECT user_id, balance, active
                FROM user_wallets
                WHERE user_id = :user_id
                FOR UPDATE
                """
            ),
            {"user_id": request.user_id},
        ).mappings().first()

        if wallet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallet not found")

        if not wallet["active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="wallet is inactive")

        wallet_balance = quantize_money(wallet["balance"])
        if wallet_balance < reserve_amount:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="insufficient wallet balance")

        request_fingerprint = f"{request.user_id}:{request.trace_id}:{request.model}:{reserve_amount}"

        try:
            session.execute(
                text(
                    """
                    INSERT INTO escrow_ledger (
                        idempotency_key,
                        user_id,
                        trace_id,
                        model,
                        request_fingerprint,
                        reserved_amount,
                        actual_amount,
                        status,
                        expires_at
                    )
                    VALUES (
                        :idempotency_key,
                        :user_id,
                        :trace_id,
                        :model,
                        :request_fingerprint,
                        :reserved_amount,
                        :actual_amount,
                        'RESERVED',
                        CURRENT_TIMESTAMP + (:reserve_ttl_seconds * INTERVAL '1 second')
                    )
                    """
                ),
                {
                    "idempotency_key": request.idempotency_key,
                    "user_id": request.user_id,
                    "trace_id": request.trace_id,
                    "model": request.model,
                    "request_fingerprint": request_fingerprint,
                    "reserved_amount": reserve_amount,
                    "actual_amount": Decimal("0.000000"),
                    "reserve_ttl_seconds": settings.reserve_ttl_seconds,
                },
            )
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_key already exists") from exc

        session.execute(
            text(
                """
                UPDATE user_wallets
                SET balance = balance - :reserved_amount,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id
                """
            ),
            {"reserved_amount": reserve_amount, "user_id": request.user_id},
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
                    'RESERVE_CREATED',
                    :amount_delta,
                    CAST(:metadata AS JSONB)
                )
                """
            ),
            {
                "idempotency_key": request.idempotency_key,
                "user_id": request.user_id,
                "amount_delta": -reserve_amount,
                "metadata": '{"trace_id": "%s", "model": "%s"}' % (request.trace_id, request.model),
            },
        )

        session.commit()

    return ReserveResponse(
        idempotency_key=request.idempotency_key,
        status="RESERVED",
        reserved_amount=reserve_amount,
        expires_in_seconds=settings.reserve_ttl_seconds,
    )
