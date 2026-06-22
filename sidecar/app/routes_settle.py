from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_internal_auth
from .db import get_db_connection
from .schemas import SettleRequest, SettleResponse

router = APIRouter(prefix="/v1/governance", tags=["settle"])


@router.post("/settle", response_model=SettleResponse, dependencies=[Depends(require_internal_auth)])
def settle_funds(request: SettleRequest) -> SettleResponse:
    with get_db_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT wallet_id
                    FROM wallets
                    WHERE tenant_id = %s
                      AND wallet_ref = %s
                    FOR UPDATE
                    """,
                    (request.tenant_id, request.wallet_ref),
                )
                wallet = cur.fetchone()
                if not wallet:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
                wallet_id = wallet[0]

                cur.execute(
                    """
                    SELECT ledger_entry_id, reservation_status, amount_reserved, amount_settled, amount_released
                    FROM ledger_entries
                    WHERE wallet_id = %s
                      AND idempotency_key = %s
                    FOR UPDATE
                    """,
                    (wallet_id, request.idempotency_key),
                )
                entry = cur.fetchone()
                if not entry:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger entry not found")

                ledger_entry_id, reservation_status, amount_reserved, amount_settled, amount_released = entry

                if reservation_status == "SETTLED":
                    return SettleResponse(
                        ledger_entry_id=str(ledger_entry_id),
                        reservation_status=reservation_status,
                        amount_settled=amount_settled,
                        amount_released=amount_released,
                    )
                if reservation_status != "RESERVED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot settle entry in {reservation_status} state",
                    )

                settled_amount: Decimal = request.realized_cost
                if settled_amount > amount_reserved:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Realized cost exceeds reserved amount; uplift path not implemented",
                    )
                released_amount = amount_reserved - settled_amount

                cur.execute(
                    """
                    UPDATE ledger_entries
                    SET reservation_status = 'SETTLED',
                        amount_settled = %s,
                        amount_released = %s,
                        settled_at = NOW(),
                        updated_at = NOW(),
                        metadata = CASE
                            WHEN %s IS NULL THEN metadata
                            ELSE metadata || jsonb_build_object('provider_request_id', %s)
                        END
                    WHERE ledger_entry_id = %s
                    """,
                    (
                        settled_amount,
                        released_amount,
                        request.provider_request_id,
                        request.provider_request_id,
                        ledger_entry_id,
                    ),
                )

                cur.execute(
                    """
                    UPDATE wallets
                    SET balance_reserved = balance_reserved - %s,
                        balance_available = balance_available + %s,
                        updated_at = NOW()
                    WHERE wallet_id = %s
                    """,
                    (amount_reserved, released_amount, wallet_id),
                )

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
                        'SETTLED_FINAL',
                        'service',
                        'sidecar',
                        jsonb_build_object(
                            'idempotency_key', %s,
                            'amount_settled', %s,
                            'amount_released', %s
                        )
                    )
                    """,
                    (ledger_entry_id, wallet_id, request.idempotency_key, settled_amount, released_amount),
                )

                if released_amount > Decimal("0"):
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
                            'SETTLEMENT_DRIFT',
                            'service',
                            'sidecar',
                            jsonb_build_object(
                                'reserved_amount', %s,
                                'settled_amount', %s,
                                'released_amount', %s
                            )
                        )
                        """,
                        (ledger_entry_id, wallet_id, amount_reserved, settled_amount, released_amount),
                    )

    return SettleResponse(
        ledger_entry_id=str(ledger_entry_id),
        reservation_status="SETTLED",
        amount_settled=settled_amount,
        amount_released=released_amount,
    )
