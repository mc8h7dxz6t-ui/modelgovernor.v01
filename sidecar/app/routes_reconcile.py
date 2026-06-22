import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, OperationalError

from app.auth import require_internal_auth
from app.db import get_db_session
from app.policy import (
    PolicyDecisionError,
    quantize_money,
    validate_provider_adjustment_request,
    validate_provider_reconciliation_request,
)
from app.schemas import (
    ModelPolicyEntry,
    ModelPolicyRegistryResponse,
    ProviderAdjustmentRequest,
    ProviderAdjustmentResponse,
    ProviderReconciliationRequest,
    ProviderReconciliationResponse,
    ReconciliationAnomalySummary,
    ReconciliationSummaryResponse,
)

router = APIRouter(tags=["reconciliation"])


@router.post(
    "/admin/provider-reconciliations",
    response_model=ProviderReconciliationResponse,
    dependencies=[Depends(require_internal_auth)],
)
def reconcile_provider(request: ProviderReconciliationRequest) -> ProviderReconciliationResponse:
    try:
        validate_provider_reconciliation_request(request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    provider_actual_amount = quantize_money(request.provider_actual_cost)

    try:
        with get_db_session() as session:
            existing = session.execute(
                text(
                    """
                    SELECT reconciliation_key, idempotency_key, provider, provider_request_id,
                           provider_actual_amount, discrepancy_amount, status, external_reference
                    FROM provider_reconciliations
                    WHERE reconciliation_key = :reconciliation_key
                    """
                ),
                {"reconciliation_key": request.reconciliation_key},
            ).mappings().first()

            if existing is not None:
                if (
                    existing["provider"] != request.provider
                    or quantize_money(existing["provider_actual_amount"]) != provider_actual_amount
                    or existing["external_reference"] != request.external_reference
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="reconciliation_key already exists with different parameters",
                    )
                if request.idempotency_key and existing["idempotency_key"] != request.idempotency_key:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="reconciliation_key already exists with different parameters",
                    )
                if request.provider_request_id and existing["provider_request_id"] != request.provider_request_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="reconciliation_key already exists with different parameters",
                    )
                return ProviderReconciliationResponse(
                    reconciliation_key=existing["reconciliation_key"],
                    idempotency_key=existing["idempotency_key"],
                    status=existing["status"],
                    discrepancy_amount=quantize_money(existing["discrepancy_amount"]),
                    reconciled=True,
                )

            ledger_row = None
            if request.idempotency_key:
                ledger_row = session.execute(
                    text(
                        """
                        SELECT idempotency_key, user_id, actual_amount, status, provider_request_id, reconciled
                        FROM escrow_ledger
                        WHERE idempotency_key = :idempotency_key
                        FOR UPDATE
                        """
                    ),
                    {"idempotency_key": request.idempotency_key},
                ).mappings().first()
            elif request.provider_request_id:
                ledger_row = session.execute(
                    text(
                        """
                        SELECT idempotency_key, user_id, actual_amount, status, provider_request_id, reconciled
                        FROM escrow_ledger
                        WHERE provider_request_id = :provider_request_id
                        FOR UPDATE
                        """
                    ),
                    {"provider_request_id": request.provider_request_id},
                ).mappings().first()

            if ledger_row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="settled ledger row not found")

            if request.provider_request_id and ledger_row["provider_request_id"] != request.provider_request_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="provider_request_id does not match the requested ledger row",
                )

            if ledger_row["status"] != "SETTLED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="only settled ledger rows can be provider reconciled",
                )

            ledger_actual_amount = quantize_money(ledger_row["actual_amount"])
            discrepancy_amount = quantize_money(provider_actual_amount - ledger_actual_amount)
            reconciliation_status = "MATCHED" if discrepancy_amount == Decimal("0.000000") else "MISMATCHED"

            session.execute(
                text(
                    """
                    INSERT INTO provider_reconciliations (
                        reconciliation_key,
                        idempotency_key,
                        provider,
                        provider_request_id,
                        provider_actual_amount,
                        ledger_actual_amount,
                        discrepancy_amount,
                        status,
                        external_reference
                    )
                    VALUES (
                        :reconciliation_key,
                        :idempotency_key,
                        :provider,
                        :provider_request_id,
                        :provider_actual_amount,
                        :ledger_actual_amount,
                        :discrepancy_amount,
                        :status,
                        :external_reference
                    )
                    """
                ),
                {
                    "reconciliation_key": request.reconciliation_key,
                    "idempotency_key": ledger_row["idempotency_key"],
                    "provider": request.provider,
                    "provider_request_id": ledger_row["provider_request_id"],
                    "provider_actual_amount": provider_actual_amount,
                    "ledger_actual_amount": ledger_actual_amount,
                    "discrepancy_amount": discrepancy_amount,
                    "status": reconciliation_status,
                    "external_reference": request.external_reference,
                },
            )

            session.execute(
                text(
                    """
                    UPDATE escrow_ledger
                    SET reconciled = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idempotency_key = :idempotency_key
                    """
                ),
                {"idempotency_key": ledger_row["idempotency_key"]},
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
                        'PROVIDER_RECONCILED',
                        :amount_delta,
                        CAST(:metadata AS JSONB)
                    )
                    """
                ),
                {
                    "idempotency_key": ledger_row["idempotency_key"],
                    "user_id": ledger_row["user_id"],
                    "amount_delta": discrepancy_amount,
                    "metadata": json.dumps(
                        {
                            "provider": request.provider,
                            "provider_request_id": ledger_row["provider_request_id"],
                            "provider_actual_amount": str(provider_actual_amount),
                            "ledger_actual_amount": str(ledger_actual_amount),
                            "reconciliation_key": request.reconciliation_key,
                            "external_reference": request.external_reference,
                            "status": reconciliation_status,
                        }
                    ),
                },
            )

            session.commit()

    except HTTPException:
        raise
    except (OperationalError, DatabaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="governance service temporarily unavailable",
        ) from exc

    return ProviderReconciliationResponse(
        reconciliation_key=request.reconciliation_key,
        idempotency_key=ledger_row["idempotency_key"],
        status=reconciliation_status,
        discrepancy_amount=discrepancy_amount,
        reconciled=True,
    )


@router.post(
    "/admin/provider-adjustments",
    response_model=ProviderAdjustmentResponse,
    dependencies=[Depends(require_internal_auth)],
)
def apply_provider_adjustment(request: ProviderAdjustmentRequest) -> ProviderAdjustmentResponse:
    try:
        validate_provider_adjustment_request(request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        with get_db_session() as session:
            existing = session.execute(
                text(
                    """
                    SELECT adjustment_key, reconciliation_key, idempotency_key,
                           corrected_actual_amount, wallet_delta
                    FROM provider_adjustments
                    WHERE adjustment_key = :adjustment_key
                    """
                ),
                {"adjustment_key": request.adjustment_key},
            ).mappings().first()

            if existing is not None:
                if existing["reconciliation_key"] != request.reconciliation_key:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="adjustment_key already exists with different parameters",
                    )
                return ProviderAdjustmentResponse(
                    adjustment_key=existing["adjustment_key"],
                    reconciliation_key=existing["reconciliation_key"],
                    idempotency_key=existing["idempotency_key"],
                    status="RESOLVED",
                    corrected_actual_amount=quantize_money(existing["corrected_actual_amount"]),
                    wallet_delta=quantize_money(existing["wallet_delta"]),
                )

            reconciliation_row = session.execute(
                text(
                    """
                    SELECT reconciliation_key, idempotency_key, provider_actual_amount, status
                    FROM provider_reconciliations
                    WHERE reconciliation_key = :reconciliation_key
                    FOR UPDATE
                    """
                ),
                {"reconciliation_key": request.reconciliation_key},
            ).mappings().first()

            if reconciliation_row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reconciliation not found")

            if reconciliation_row["status"] == "MATCHED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="matched reconciliations do not require adjustment",
                )

            if reconciliation_row["status"] == "RESOLVED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="reconciliation already resolved",
                )

            ledger_row = session.execute(
                text(
                    """
                    SELECT idempotency_key, user_id, actual_amount, status
                    FROM escrow_ledger
                    WHERE idempotency_key = :idempotency_key
                    FOR UPDATE
                    """
                ),
                {"idempotency_key": reconciliation_row["idempotency_key"]},
            ).mappings().first()

            if ledger_row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ledger row not found")

            if ledger_row["status"] != "SETTLED":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="only settled ledger rows can be adjusted",
                )

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

            prior_actual_amount = quantize_money(ledger_row["actual_amount"])
            corrected_actual_amount = quantize_money(reconciliation_row["provider_actual_amount"])
            wallet_delta = quantize_money(prior_actual_amount - corrected_actual_amount)

            if wallet_delta < 0 and quantize_money(wallet_row["balance"]) < abs(wallet_delta):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="insufficient wallet balance for provider adjustment",
                )

            session.execute(
                text(
                    """
                    UPDATE escrow_ledger
                    SET actual_amount = :actual_amount,
                        reconciled = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE idempotency_key = :idempotency_key
                    """
                ),
                {
                    "actual_amount": corrected_actual_amount,
                    "idempotency_key": ledger_row["idempotency_key"],
                },
            )

            session.execute(
                text(
                    """
                    UPDATE user_wallets
                    SET balance = balance + :wallet_delta,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                    """
                ),
                {"wallet_delta": wallet_delta, "user_id": ledger_row["user_id"]},
            )

            session.execute(
                text(
                    """
                    UPDATE provider_reconciliations
                    SET status = 'RESOLVED',
                        resolved_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE reconciliation_key = :reconciliation_key
                    """
                ),
                {"reconciliation_key": reconciliation_row["reconciliation_key"]},
            )

            session.execute(
                text(
                    """
                    INSERT INTO provider_adjustments (
                        adjustment_key,
                        reconciliation_key,
                        idempotency_key,
                        prior_actual_amount,
                        corrected_actual_amount,
                        wallet_delta,
                        reason
                    )
                    VALUES (
                        :adjustment_key,
                        :reconciliation_key,
                        :idempotency_key,
                        :prior_actual_amount,
                        :corrected_actual_amount,
                        :wallet_delta,
                        :reason
                    )
                    """
                ),
                {
                    "adjustment_key": request.adjustment_key,
                    "reconciliation_key": reconciliation_row["reconciliation_key"],
                    "idempotency_key": ledger_row["idempotency_key"],
                    "prior_actual_amount": prior_actual_amount,
                    "corrected_actual_amount": corrected_actual_amount,
                    "wallet_delta": wallet_delta,
                    "reason": request.reason.strip(),
                },
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
                        'PROVIDER_ADJUSTMENT',
                        :amount_delta,
                        CAST(:metadata AS JSONB)
                    )
                    """
                ),
                {
                    "idempotency_key": ledger_row["idempotency_key"],
                    "user_id": ledger_row["user_id"],
                    "amount_delta": wallet_delta,
                    "metadata": json.dumps(
                        {
                            "adjustment_key": request.adjustment_key,
                            "reconciliation_key": reconciliation_row["reconciliation_key"],
                            "prior_actual_amount": str(prior_actual_amount),
                            "corrected_actual_amount": str(corrected_actual_amount),
                            "reason": request.reason.strip(),
                        }
                    ),
                },
            )

            session.commit()

    except HTTPException:
        raise
    except (OperationalError, DatabaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="governance service temporarily unavailable",
        ) from exc

    return ProviderAdjustmentResponse(
        adjustment_key=request.adjustment_key,
        reconciliation_key=reconciliation_row["reconciliation_key"],
        idempotency_key=ledger_row["idempotency_key"],
        status="RESOLVED",
        corrected_actual_amount=corrected_actual_amount,
        wallet_delta=wallet_delta,
    )


@router.get(
    "/admin/reconciliation-summary",
    response_model=ReconciliationSummaryResponse,
    dependencies=[Depends(require_internal_auth)],
)
def reconciliation_summary() -> ReconciliationSummaryResponse:
    try:
        with get_db_session() as session:
            counts_row = session.execute(
                text(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'MATCHED')   AS matched_count,
                        COUNT(*) FILTER (WHERE status = 'MISMATCHED') AS mismatched_count,
                        COUNT(*) FILTER (WHERE status = 'RESOLVED')  AS resolved_count,
                        COALESCE(
                            SUM(discrepancy_amount) FILTER (WHERE status = 'MISMATCHED'),
                            0
                        ) AS total_unresolved_discrepancy
                    FROM provider_reconciliations
                    """
                )
            ).first()

            anomaly_rows = session.execute(
                text(
                    """
                    SELECT reconciliation_key, idempotency_key, provider,
                           discrepancy_amount, created_at
                    FROM provider_reconciliations
                    WHERE status = 'MISMATCHED'
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                )
            ).mappings().all()

    except (OperationalError, DatabaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="governance service temporarily unavailable",
        ) from exc

    anomalies = [
        ReconciliationAnomalySummary(
            reconciliation_key=row["reconciliation_key"],
            idempotency_key=row["idempotency_key"],
            provider=row["provider"],
            discrepancy_amount=quantize_money(Decimal(str(row["discrepancy_amount"]))),
            created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        )
        for row in anomaly_rows
    ]

    return ReconciliationSummaryResponse(
        matched_count=counts_row[0] if counts_row else 0,
        mismatched_count=counts_row[1] if counts_row else 0,
        resolved_count=counts_row[2] if counts_row else 0,
        total_unresolved_discrepancy=quantize_money(Decimal(str(counts_row[3]))) if counts_row else Decimal("0"),
        anomalies=anomalies,
    )


@router.get(
    "/admin/models",
    response_model=ModelPolicyRegistryResponse,
    dependencies=[Depends(require_internal_auth)],
)
def list_model_policy() -> ModelPolicyRegistryResponse:
    try:
        with get_db_session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT model_name, provider, governance_tier, enabled,
                           max_input_tokens, max_output_tokens, max_cost_per_request,
                           max_cost_per_trace, stream_allowed, fallback_price_per_token
                    FROM model_policy_registry
                    ORDER BY
                        CASE governance_tier
                            WHEN 'FRONTIER' THEN 1
                            WHEN 'STANDARD' THEN 2
                            WHEN 'BUDGET'   THEN 3
                            ELSE 4
                        END,
                        provider,
                        model_name
                    """
                )
            ).mappings().all()

    except (OperationalError, DatabaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="governance service temporarily unavailable",
        ) from exc

    models = [
        ModelPolicyEntry(
            model_name=row["model_name"],
            provider=row["provider"],
            governance_tier=row["governance_tier"],
            enabled=row["enabled"],
            max_input_tokens=row["max_input_tokens"],
            max_output_tokens=row["max_output_tokens"],
            max_cost_per_request=quantize_money(Decimal(str(row["max_cost_per_request"]))),
            max_cost_per_trace=quantize_money(Decimal(str(row["max_cost_per_trace"]))),
            stream_allowed=row["stream_allowed"],
            fallback_price_per_token=quantize_money(Decimal(str(row["fallback_price_per_token"]))),
        )
        for row in rows
    ]

    return ModelPolicyRegistryResponse(
        models=models,
        total_count=len(models),
        enabled_count=sum(1 for m in models if m.enabled),
        budget_count=sum(1 for m in models if m.governance_tier == "BUDGET"),
        standard_count=sum(1 for m in models if m.governance_tier == "STANDARD"),
        frontier_count=sum(1 for m in models if m.governance_tier == "FRONTIER"),
    )
