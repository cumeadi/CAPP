"""
Airtel Money Webhook API Endpoints

Provides webhook endpoints for Airtel Money callbacks including:
- Push Payment callbacks
- Disbursement callbacks
- Payment notifications
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
from ....services.airtel_money_integration import AirtelMoneyService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks/airtel", tags=["webhooks", "airtel-money"])


# =============================================================================
# Callback Processing Functions
# =============================================================================

async def process_payment_callback(
    callback_data: Dict[str, Any],
    db_session: AsyncSession
) -> None:
    """
    Process Airtel Money payment callback

    Args:
        callback_data: Callback data from Airtel Money
        db_session: Database session
    """
    try:
        # Extract transaction data from Airtel Money callback format
        # Airtel Money callback structure:
        # {
        #   "transaction": {
        #     "id": "airtel_transaction_id",
        #     "status": "TS" | "TIP" | "TF",  (Success, In Progress, Failed)
        #     "message": "Success message"
        #   },
        #   "data": {
        #     "transaction": {
        #       "id": "merchant_transaction_id",
        #       "amount": "1000.00",
        #       "currency": "KES",
        #       ...
        #     }
        #   }
        # }

        transaction = callback_data.get("transaction", {})
        data_transaction = callback_data.get("data", {}).get("transaction", {})

        airtel_transaction_id = transaction.get("id")
        merchant_transaction_id = data_transaction.get("id")
        status_code = transaction.get("status")  # TS, TIP, TF
        status_message = transaction.get("message")
        amount = data_transaction.get("amount")
        currency = data_transaction.get("currency")

        # Map Airtel status codes to our status
        status_mapping = {
            "TS": "successful",  # Transaction Successful
            "TIP": "pending",    # Transaction In Progress
            "TF": "failed"       # Transaction Failed
        }
        status_value = status_mapping.get(status_code, "unknown")

        logger.info(
            "Processing Airtel Money payment callback",
            airtel_transaction_id=airtel_transaction_id,
            merchant_transaction_id=merchant_transaction_id,
            status=status_value,
            amount=amount
        )

        # Store callback in database
        mmo_callback = MMOCallback(
            provider="airtel_money",
            provider_transaction_id=airtel_transaction_id,
            callback_data=json.dumps(callback_data),
            callback_type="payment",
            status=status_value,
            amount=float(amount) if amount else None,
            currency=currency,
            external_reference=merchant_transaction_id,
            received_at=datetime.now(timezone.utc)
        )

        db_session.add(mmo_callback)

        # TODO: Update payment status based on callback
        # payment_repo = PaymentRepository(db_session)
        # if merchant_transaction_id:
        #     await payment_repo.update_payment_status_by_reference(
        #         reference=merchant_transaction_id,
        #         status="completed" if status_code == "TS" else "failed" if status_code == "TF" else "processing",
        #         provider_transaction_id=airtel_transaction_id
        #     )

        await db_session.commit()

        logger.info(
            "Airtel Money payment callback processed",
            airtel_transaction_id=airtel_transaction_id,
            status=status_value
        )

    except Exception as e:
        logger.error(
            "Error processing Airtel Money payment callback",
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
    Process Airtel Money disbursement callback

    Args:
        callback_data: Callback data from Airtel Money
        db_session: Database session
    """
    try:
        # Extract transaction data
        transaction = callback_data.get("transaction", {})
        data_transaction = callback_data.get("data", {}).get("transaction", {})

        airtel_transaction_id = transaction.get("id")
        merchant_transaction_id = data_transaction.get("id")
        status_code = transaction.get("status")
        status_message = transaction.get("message")
        amount = data_transaction.get("amount")
        currency = data_transaction.get("currency")

        # Map status codes
        status_mapping = {
            "TS": "successful",
            "TIP": "pending",
            "TF": "failed"
        }
        status_value = status_mapping.get(status_code, "unknown")

        logger.info(
            "Processing Airtel Money disbursement callback",
            airtel_transaction_id=airtel_transaction_id,
            merchant_transaction_id=merchant_transaction_id,
            status=status_value,
            amount=amount
        )

        # Store callback in database
        mmo_callback = MMOCallback(
            provider="airtel_money",
            provider_transaction_id=airtel_transaction_id,
            callback_data=json.dumps(callback_data),
            callback_type="disbursement",
            status=status_value,
            amount=float(amount) if amount else None,
            currency=currency,
            external_reference=merchant_transaction_id,
            received_at=datetime.now(timezone.utc)
        )

        db_session.add(mmo_callback)
        await db_session.commit()

        logger.info(
            "Airtel Money disbursement callback processed",
            airtel_transaction_id=airtel_transaction_id,
            status=status_value
        )

    except Exception as e:
        logger.error(
            "Error processing Airtel Money disbursement callback",
            error=str(e),
            callback_data=callback_data,
            exc_info=True
        )
        await db_session.rollback()
        raise


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/payment")
async def airtel_payment_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Airtel Money payment callback endpoint

    This endpoint receives callbacks from Airtel Money when a push payment
    or payment enquiry transaction completes.

    Returns:
        JSONResponse: Immediate acknowledgment in Airtel Money format
    """
    try:
        # Parse callback data
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        # Extract transaction info for logging
        transaction = callback_data.get("transaction", {})
        logger.info(
            "Airtel Money payment callback received",
            transaction_id=transaction.get("id"),
            status=transaction.get("status")
        )

        # Process callback in background to return immediately
        background_tasks.add_task(
            process_payment_callback,
            callback_data,
            db
        )

        # Return immediate acknowledgment in Airtel Money format
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": {
                    "code": "200",
                    "message": "Callback received successfully",
                    "success": True
                }
            }
        )

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in Airtel Money callback", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": {
                    "code": "400",
                    "message": "Invalid JSON",
                    "success": False
                }
            }
        )
    except Exception as e:
        logger.error(
            "Error handling Airtel Money payment callback",
            error=str(e),
            exc_info=True
        )
        # Still return 200 to prevent Airtel from retrying
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": {
                    "code": "200",
                    "message": "Callback received",
                    "success": True
                }
            }
        )


@router.post("/disbursement")
async def airtel_disbursement_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Airtel Money disbursement callback endpoint

    This endpoint receives callbacks from Airtel Money when a disbursement
    transaction completes.

    Returns:
        JSONResponse: Immediate acknowledgment in Airtel Money format
    """
    try:
        # Parse callback data
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        # Extract transaction info for logging
        transaction = callback_data.get("transaction", {})
        logger.info(
            "Airtel Money disbursement callback received",
            transaction_id=transaction.get("id"),
            status=transaction.get("status")
        )

        # Process callback in background
        background_tasks.add_task(
            process_disbursement_callback,
            callback_data,
            db
        )

        # Return immediate acknowledgment in Airtel Money format
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": {
                    "code": "200",
                    "message": "Callback received successfully",
                    "success": True
                }
            }
        )

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in Airtel Money callback", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": {
                    "code": "400",
                    "message": "Invalid JSON",
                    "success": False
                }
            }
        )
    except Exception as e:
        logger.error(
            "Error handling Airtel Money disbursement callback",
            error=str(e),
            exc_info=True
        )
        # Still return 200 to prevent Airtel from retrying
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": {
                    "code": "200",
                    "message": "Callback received",
                    "success": True
                }
            }
        )


@router.post("/notification")
async def airtel_notification_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Airtel Money general notification callback endpoint

    This endpoint receives various notifications from Airtel Money including
    payment confirmations, account updates, etc.

    Returns:
        JSONResponse: Immediate acknowledgment
    """
    try:
        # Parse callback data
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Airtel Money notification received",
            notification_type=callback_data.get("type"),
            data=callback_data
        )

        # Store notification in database
        mmo_callback = MMOCallback(
            provider="airtel_money",
            provider_transaction_id=callback_data.get("id", "notification"),
            callback_data=json.dumps(callback_data),
            callback_type="notification",
            status="received",
            received_at=datetime.now(timezone.utc)
        )

        db.add(mmo_callback)
        await db.commit()

        # Return immediate acknowledgment
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": {
                    "code": "200",
                    "message": "Notification received successfully",
                    "success": True
                }
            }
        )

    except Exception as e:
        logger.error(
            "Error handling Airtel Money notification",
            error=str(e),
            exc_info=True
        )
        # Still return 200 to prevent Airtel from retrying
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": {
                    "code": "200",
                    "message": "Notification received",
                    "success": True
                }
            }
        )


@router.get("/health")
async def airtel_webhook_health():
    """Health check endpoint for Airtel Money webhooks"""
    return {"status": "healthy", "provider": "airtel_money"}
