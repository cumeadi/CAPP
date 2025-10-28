"""
MTN Mobile Money Webhook API Endpoints

Provides webhook endpoints for MTN MoMo callbacks including:
- Request to Pay callbacks (Collections)
- Transfer callbacks (Disbursements)
- Remittance callbacks
"""

from typing import Dict, Any, Optional
from uuid import UUID
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, status, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ....core.database import get_db, MMOCallback
from ....repositories.payment import PaymentRepository
from ....services.mtn_momo_integration import MTNMoMoService, MTNMoMoProduct

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks/mtn", tags=["webhooks", "mtn-momo"])


# =============================================================================
# Callback Processing Functions
# =============================================================================

async def process_collection_callback(
    callback_data: Dict[str, Any],
    db_session: AsyncSession
) -> None:
    """
    Process MTN MoMo Collection (Request to Pay) callback

    Args:
        callback_data: Callback data from MTN MoMo
        db_session: Database session
    """
    try:
        # Extract transaction data
        reference_id = callback_data.get("referenceId")
        external_id = callback_data.get("externalId")
        status_value = callback_data.get("status")  # PENDING, SUCCESSFUL, FAILED
        amount = callback_data.get("amount")
        currency = callback_data.get("currency")
        financial_transaction_id = callback_data.get("financialTransactionId")
        reason = callback_data.get("reason")

        logger.info(
            "Processing MTN MoMo Collection callback",
            reference_id=reference_id,
            external_id=external_id,
            status=status_value,
            amount=amount
        )

        # Store callback in database
        mmo_callback = MMOCallback(
            provider="mtn_mobile_money",
            provider_transaction_id=reference_id,
            callback_data=json.dumps(callback_data),
            callback_type="collection",
            status=status_value.lower() if status_value else "unknown",
            amount=float(amount) if amount else None,
            currency=currency,
            external_reference=external_id,
            received_at=datetime.now(timezone.utc)
        )

        db_session.add(mmo_callback)

        # TODO: Update payment status based on callback
        # payment_repo = PaymentRepository(db_session)
        # if external_id:
        #     await payment_repo.update_payment_status_by_reference(
        #         reference=external_id,
        #         status="completed" if status_value == "SUCCESSFUL" else "failed",
        #         provider_transaction_id=financial_transaction_id
        #     )

        await db_session.commit()

        logger.info(
            "MTN MoMo Collection callback processed",
            reference_id=reference_id,
            status=status_value
        )

    except Exception as e:
        logger.error(
            "Error processing MTN MoMo Collection callback",
            error=str(e),
            callback_data=callback_data,
            exc_info=True
        )
        await db_session.rollback()
        raise


async def process_disbursement_callback(
    callback_data: Dict[str, Any],
    db_session: AsyncSession
) -> None:
    """
    Process MTN MoMo Disbursement (Transfer) callback

    Args:
        callback_data: Callback data from MTN MoMo
        db_session: Database session
    """
    try:
        # Extract transaction data
        reference_id = callback_data.get("referenceId")
        external_id = callback_data.get("externalId")
        status_value = callback_data.get("status")
        amount = callback_data.get("amount")
        currency = callback_data.get("currency")
        financial_transaction_id = callback_data.get("financialTransactionId")

        logger.info(
            "Processing MTN MoMo Disbursement callback",
            reference_id=reference_id,
            external_id=external_id,
            status=status_value,
            amount=amount
        )

        # Store callback in database
        mmo_callback = MMOCallback(
            provider="mtn_mobile_money",
            provider_transaction_id=reference_id,
            callback_data=json.dumps(callback_data),
            callback_type="disbursement",
            status=status_value.lower() if status_value else "unknown",
            amount=float(amount) if amount else None,
            currency=currency,
            external_reference=external_id,
            received_at=datetime.now(timezone.utc)
        )

        db_session.add(mmo_callback)
        await db_session.commit()

        logger.info(
            "MTN MoMo Disbursement callback processed",
            reference_id=reference_id,
            status=status_value
        )

    except Exception as e:
        logger.error(
            "Error processing MTN MoMo Disbursement callback",
            error=str(e),
            callback_data=callback_data,
            exc_info=True
        )
        await db_session.rollback()
        raise


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/collection")
async def mtn_collection_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    MTN Mobile Money Collection (Request to Pay) callback endpoint

    This endpoint receives callbacks from MTN MoMo when a Request to Pay
    transaction completes (successful, failed, or timeout).

    Returns:
        JSONResponse: Immediate acknowledgment
    """
    try:
        # Parse callback data
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "MTN MoMo Collection callback received",
            reference_id=callback_data.get("referenceId"),
            status=callback_data.get("status")
        )

        # Process callback in background to return immediately
        background_tasks.add_task(
            process_collection_callback,
            callback_data,
            db
        )

        # Return immediate acknowledgment
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "accepted", "message": "Callback received"}
        )

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in MTN MoMo callback", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": "Invalid JSON"}
        )
    except Exception as e:
        logger.error(
            "Error handling MTN MoMo Collection callback",
            error=str(e),
            exc_info=True
        )
        # Still return 200 to prevent MTN from retrying
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "accepted", "message": "Callback received"}
        )


@router.post("/disbursement")
async def mtn_disbursement_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    MTN Mobile Money Disbursement (Transfer) callback endpoint

    This endpoint receives callbacks from MTN MoMo when a Transfer/Disbursement
    transaction completes.

    Returns:
        JSONResponse: Immediate acknowledgment
    """
    try:
        # Parse callback data
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "MTN MoMo Disbursement callback received",
            reference_id=callback_data.get("referenceId"),
            status=callback_data.get("status")
        )

        # Process callback in background
        background_tasks.add_task(
            process_disbursement_callback,
            callback_data,
            db
        )

        # Return immediate acknowledgment
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "accepted", "message": "Callback received"}
        )

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in MTN MoMo callback", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": "Invalid JSON"}
        )
    except Exception as e:
        logger.error(
            "Error handling MTN MoMo Disbursement callback",
            error=str(e),
            exc_info=True
        )
        # Still return 200 to prevent MTN from retrying
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "accepted", "message": "Callback received"}
        )


@router.post("/remittance")
async def mtn_remittance_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    MTN Mobile Money Remittance callback endpoint

    This endpoint receives callbacks from MTN MoMo for cross-border remittance
    transactions.

    Returns:
        JSONResponse: Immediate acknowledgment
    """
    try:
        # Parse callback data
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "MTN MoMo Remittance callback received",
            reference_id=callback_data.get("referenceId"),
            status=callback_data.get("status")
        )

        # Store callback in database
        mmo_callback = MMOCallback(
            provider="mtn_mobile_money",
            provider_transaction_id=callback_data.get("referenceId"),
            callback_data=json.dumps(callback_data),
            callback_type="remittance",
            status=callback_data.get("status", "").lower(),
            amount=float(callback_data.get("amount")) if callback_data.get("amount") else None,
            currency=callback_data.get("currency"),
            external_reference=callback_data.get("externalId"),
            received_at=datetime.now(timezone.utc)
        )

        db.add(mmo_callback)
        await db.commit()

        # Return immediate acknowledgment
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "accepted", "message": "Callback received"}
        )

    except Exception as e:
        logger.error(
            "Error handling MTN MoMo Remittance callback",
            error=str(e),
            exc_info=True
        )
        # Still return 200 to prevent MTN from retrying
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "accepted", "message": "Callback received"}
        )


@router.get("/health")
async def mtn_webhook_health():
    """Health check endpoint for MTN MoMo webhooks"""
    return {"status": "healthy", "provider": "mtn_mobile_money"}
