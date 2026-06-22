from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_internal_auth
from .config import settings
from .db import get_db_connection
from .schemas import ReserveRequest, ReserveResponse
from .policy import compute_reservation_amount

router = APIRouter(prefix="/v1/governance", tags=["reserve"])


@router.post("/reserve", response_model=ReserveResponse, dependencies=[Depends(require_internal_auth)])
def reserve_funds(request: ReserveRequest) -> ReserveResponse:
    reservation_amount: Decimal = compute_reservation_amount(request.estimated_cost)
    reserved_until = datetime.now(UTC) + timedelta(seconds=settings.default_reservation_ttl_seconds)

    with get_db_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT wallet_id, balance_available
                    FROM wallets
                    WHERE tenant_id = %s
                      AND wallet_ref = %s
                      AND is_active = TRUE
                    FOR UPDATE
                    """,
                    (request.tenant_id, request.wallet_ref),
                )
                wallet = cur.fetchone()
                if not wallet:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

                wallet_id, balance_available = wallet

                cur.execute(
                    """
                    SELECT policy_id, enabled, max_cost_per_request
                    FROM model_policies
                    WHERE tenant_id = %s
                      AND provider = %s
                      AND model_name = %s
                    """,
                    (request.tenant_id, request.provider, request.model_name),
                )
                policy = cur.fetchone()
                if not policy:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Model policy not found for tenant/provider/model",
                    )

                policy_id, enabled, max_cost_per_request = policy
                if not enabled:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Model policy disabled")
                if reservation_amount > max_cost_per_request:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Estimated cost exceeds policy max cost per request",
                    )

                cur.execute(
                    """
                    SELECT ledger_entry_id, reservation_status, amount_reserved, reserved_until
                    FROM ledger_entries
                    WHERE wallet_id = %s
                      AND idempotency_key = %s
                    FOR UPDATE
                    """,
                    (wallet_id, request.idempotency_key),
                )
                existing_entry = cur.fetchone()
                if existing_entry:
                    ledger_entry_id, reservation_status, amount_reserved, existing_reserved_until = existing_entry
                    if reservation_status != "RESERVED":
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Idempotency key already finalized",
                        )
                    return ReserveResponse(
                        ledger_entry_id=str(ledger_entry_id),
                        reservation_status=reservation_status,
                        amount_reserved=amount_reserved,
                        reserved_until=existing_reserved_until.isoformat(),
                    )

                if balance_available < reservation_amount:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Insufficient wallet balance for reservation",
                    )

                cur.execute(
                    """
                    UPDATE wallets
                    SET balance_available = balance_available - %s,
                        balance_reserved = balance_reserved + %s,
                        updated_at = NOW()
                    WHERE wallet_id = %s
                    """,
                    (reservation_amount, reservation_amount, wallet_id),
                )

                cur.execute(
                    """
                    INSERT INTO ledger_entries (
                        wallet_id,
                        policy_id,
                        request_id,
                        idempotency_key,
                        reservation_status,
                        amount_reserved,
                        amount_settled,
                        amount_released,
                        reserved_until,
                        metadata
                    ) VALUES (
                        %s, %s, %s, %s, 'RESERVED', %s, 0, 0, %s,
                        jsonb_build_object(
                            'tenant_id', %s,
                            'provider', %s,
                            'model_name', %s
                        )
                    )
                    RETURNING ledger_entry_id, reservation_status, amount_reserved, reserved_until
                    """,
                    (
                        wallet_id,
                        policy_id,
                        request.request_id,
                        request.idempotency_key,
                        reservation_amount,
                        reserved_until,
                        request.tenant_id,
                        request.provider,
                        request.model_name,
                    ),
                )
                ledger_entry_id, reservation_status, amount_reserved, reserved_until_db = cur.fetchone()

                cur.execute(
                    """
                    INSERT INTO audit_events (
                        ledger_entry_id,
                        wallet_id,
                        event_type,
                        actor_type,
                        actor_id,
                        event_payload
                    ) VALUES (
                        %s,
                        %s,
                        'RESERVE_CREATED',
                        'service',
                        'sidecar',
                        jsonb_build_object(
                            'request_id', %s,
                            'idempotency_key', %s,
                            'amount_reserved', %s
                        )
                    )
                    """,
                    (
                        ledger_entry_id,
                        wallet_id,
                        request.request_id,
                        request.idempotency_key,
                        amount_reserved,
                    ),
                )

    return ReserveResponse(
        ledger_entry_id=str(ledger_entry_id),
        reservation_status=reservation_status,
        amount_reserved=amount_reserved,
        reserved_until=reserved_until_db.isoformat(),
    )
