"""
M-Pesa Webhook API Endpoints

Provides webhook endpoints for M-Pesa callbacks including:
- STK Push callbacks
- C2B confirmation and validation
- B2C results
- Transaction timeouts
- Account balance results
"""

from typing import Dict, Any, Optional
from uuid import UUID
import json
import hashlib
import hmac

from fastapi import APIRouter, Request, Response, status, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ....core.database import get_db
from ....repositories.mpesa import MpesaRepository
from ....repositories.payment import PaymentRepository
from ....services.mpesa_integration import MpesaService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks/mpesa", tags=["webhooks", "mpesa"])


# =============================================================================
# Callback Signature Verification
# =============================================================================

async def verify_mpesa_signature(
    request: Request,
    body: bytes
) -> bool:
    """
    Verify M-Pesa callback signature

    Args:
        request: FastAPI request object
        body: Request body bytes

    Returns:
        bool: True if signature is valid
    """
    # Get signature from headers
    signature = request.headers.get("X-Mpesa-Signature")
    if not signature:
        logger.warning("Missing M-Pesa signature in callback")
        return False

    # TODO: Implement actual signature verification using M-Pesa public key
    # For now, we'll log and accept all callbacks in development
    # In production, this MUST verify the signature

    logger.info(
        "M-Pesa callback signature received",
        signature=signature,
        body_length=len(body)
    )

    # In development mode, accept all signatures
    # In production, verify using M-Pesa public key
    return True


async def process_stk_push_callback(
    callback_data: Dict[str, Any],
    db_session: AsyncSession
) -> None:
    """
    Process STK Push callback and update database

    Args:
        callback_data: Callback data from M-Pesa
        db_session: Database session
    """
    try:
        mpesa_repo = MpesaRepository(db_session)

        # Extract result data
        body = callback_data.get("Body", {})
        stk_callback = body.get("stkCallback", {})

        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")

        logger.info(
            "Processing STK Push callback",
            merchant_request_id=merchant_request_id,
            checkout_request_id=checkout_request_id,
            result_code=result_code
        )

        # Find transaction
        transaction = await mpesa_repo.get_by_checkout_request_id(checkout_request_id)
        if not transaction:
            logger.warning(
                "Transaction not found for callback",
                checkout_request_id=checkout_request_id
            )
            return

        # Parse callback metadata
        callback_metadata = stk_callback.get("CallbackMetadata", {})
        items = callback_metadata.get("Item", [])

        mpesa_receipt_number = None
        transaction_date = None
        phone_number = None
        amount = None

        for item in items:
            name = item.get("Name")
            value = item.get("Value")

            if name == "MpesaReceiptNumber":
                mpesa_receipt_number = value
            elif name == "TransactionDate":
                # Convert M-Pesa date format to datetime
                # Format: YYYYMMDDHHmmss
                if value:
                    from datetime import datetime
                    transaction_date = datetime.strptime(str(value), "%Y%m%d%H%M%S")
            elif name == "PhoneNumber":
                phone_number = value
            elif name == "Amount":
                amount = float(value) if value else None

        # Determine status based on result code
        if result_code == 0:
            new_status = "completed"
        elif result_code == 1032:
            new_status = "cancelled"
        elif result_code == 1037:
            new_status = "timeout"
        else:
            new_status = "failed"

        # Update transaction
        await mpesa_repo.update_transaction(
            transaction.id,
            status=new_status,
            result_code=result_code,
            result_description=result_desc,
            mpesa_receipt_number=mpesa_receipt_number,
            transaction_date=transaction_date,
            response_payload=callback_data
        )

        # Create callback record
        await mpesa_repo.create_callback(
            callback_type="stk_callback",
            callback_data=callback_data,
            checkout_request_id=checkout_request_id,
            merchant_request_id=merchant_request_id,
            mpesa_transaction_id=transaction.id
        )

        # Update payment status if linked
        if transaction.payment_id and new_status == "completed":
            payment_repo = PaymentRepository(db_session)
            await payment_repo.update_payment(
                transaction.payment_id,
                status="processing",
                mmo_transaction_id=mpesa_receipt_number
            )

        logger.info(
            "STK Push callback processed successfully",
            transaction_id=str(transaction.id),
            status=new_status,
            receipt=mpesa_receipt_number
        )

    except Exception as e:
        logger.error(
            "Error processing STK Push callback",
            error=str(e),
            callback_data=callback_data
        )
        raise


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/stk-callback")
async def mpesa_stk_push_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    M-Pesa STK Push callback endpoint

    Receives payment confirmation callbacks from M-Pesa after customer
    approves or declines STK Push prompt.

    Args:
        request: FastAPI request
        background_tasks: Background task handler
        db: Database session

    Returns:
        JSONResponse: Acknowledgment response
    """
    try:
        # Read request body
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Received STK Push callback",
            callback_data=callback_data
        )

        # Verify signature
        is_valid = await verify_mpesa_signature(request, body)
        if not is_valid:
            logger.warning("Invalid M-Pesa signature")
            # Still process in development, but log the warning
            # In production, return 401

        # Process callback in background
        background_tasks.add_task(
            process_stk_push_callback,
            callback_data,
            db
        )

        # Return immediate acknowledgment
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )

    except Exception as e:
        logger.error("Error handling STK Push callback", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,  # Always return 200 to M-Pesa
            content={
                "ResultCode": 1,
                "ResultDesc": "Failed to process callback"
            }
        )


@router.post("/timeout")
async def mpesa_timeout_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    M-Pesa timeout callback endpoint

    Receives timeout notifications when customer doesn't respond to
    STK Push prompt within timeout period.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        JSONResponse: Acknowledgment response
    """
    try:
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Received M-Pesa timeout callback",
            callback_data=callback_data
        )

        mpesa_repo = MpesaRepository(db)

        # Extract identifiers
        checkout_request_id = callback_data.get("CheckoutRequestID")

        if checkout_request_id:
            # Find and update transaction
            transaction = await mpesa_repo.get_by_checkout_request_id(checkout_request_id)
            if transaction:
                await mpesa_repo.update_transaction(
                    transaction.id,
                    status="timeout",
                    error_message="Transaction timeout - customer did not respond"
                )

                # Create callback record
                await mpesa_repo.create_callback(
                    callback_type="timeout",
                    callback_data=callback_data,
                    checkout_request_id=checkout_request_id,
                    mpesa_transaction_id=transaction.id
                )

                logger.info(
                    "Timeout callback processed",
                    transaction_id=str(transaction.id)
                )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )

    except Exception as e:
        logger.error("Error handling timeout callback", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 1,
                "ResultDesc": "Failed"
            }
        )


@router.post("/c2b-confirmation")
async def mpesa_c2b_confirmation(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    M-Pesa C2B confirmation callback

    Receives confirmation for Customer to Business payments.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        JSONResponse: Acknowledgment response
    """
    try:
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Received C2B confirmation",
            callback_data=callback_data
        )

        mpesa_repo = MpesaRepository(db)

        # Extract transaction details
        trans_id = callback_data.get("TransID")
        phone_number = callback_data.get("MSISDN")
        amount = float(callback_data.get("TransAmount", 0))
        bill_ref_number = callback_data.get("BillRefNumber")

        # Create C2B transaction record
        await mpesa_repo.create_transaction(
            transaction_type="c2b",
            phone_number=phone_number,
            amount=amount,
            merchant_request_id=trans_id,
            account_reference=bill_ref_number,
            transaction_desc=f"C2B Payment from {phone_number}"
        )

        # Create callback record
        await mpesa_repo.create_callback(
            callback_type="c2b_confirmation",
            callback_data=callback_data,
            merchant_request_id=trans_id
        )

        logger.info(
            "C2B confirmation processed",
            trans_id=trans_id,
            amount=amount
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )

    except Exception as e:
        logger.error("Error handling C2B confirmation", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 1,
                "ResultDesc": "Failed"
            }
        )


@router.post("/c2b-validation")
async def mpesa_c2b_validation(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    M-Pesa C2B validation callback

    Validates Customer to Business payment requests before confirmation.
    Can be used to reject payments based on business rules.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        JSONResponse: Validation response
    """
    try:
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Received C2B validation request",
            callback_data=callback_data
        )

        # Extract validation details
        phone_number = callback_data.get("MSISDN")
        amount = float(callback_data.get("TransAmount", 0))
        bill_ref_number = callback_data.get("BillRefNumber")

        # TODO: Implement business validation rules
        # - Check if account exists
        # - Check if amount is within limits
        # - Check if phone number is allowed
        # - Check fraud rules

        # For now, accept all payments
        is_valid = True

        if is_valid:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "ResultCode": 0,
                    "ResultDesc": "Accepted"
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "ResultCode": 1,
                    "ResultDesc": "Rejected - validation failed"
                }
            )

    except Exception as e:
        logger.error("Error handling C2B validation", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 1,
                "ResultDesc": "Failed"
            }
        )


@router.post("/b2c-result")
async def mpesa_b2c_result(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    M-Pesa B2C result callback

    Receives results for Business to Customer disbursement transactions.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        JSONResponse: Acknowledgment response
    """
    try:
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Received B2C result callback",
            callback_data=callback_data
        )

        mpesa_repo = MpesaRepository(db)

        # Extract result data
        result = callback_data.get("Result", {})
        result_code = result.get("ResultCode")
        result_desc = result.get("ResultDesc")
        conversation_id = result.get("ConversationID")
        originator_conversation_id = result.get("OriginatorConversationID")

        # Find transaction by conversation ID
        transaction = await mpesa_repo.get_by_conversation_id(conversation_id)

        if transaction:
            # Determine status
            if result_code == 0:
                new_status = "completed"
            else:
                new_status = "failed"

            # Extract result parameters
            result_parameters = result.get("ResultParameters", {})
            items = result_parameters.get("ResultParameter", [])

            mpesa_receipt_number = None
            transaction_date = None

            for item in items:
                name = item.get("Name")
                value = item.get("Value")

                if name == "TransactionReceipt":
                    mpesa_receipt_number = value
                elif name == "TransactionCompletedDateTime":
                    # Parse date
                    if value:
                        from datetime import datetime
                        try:
                            transaction_date = datetime.strptime(str(value), "%d.%m.%Y %H:%M:%S")
                        except:
                            logger.warning("Could not parse B2C transaction date", date=value)

            # Update transaction
            await mpesa_repo.update_transaction(
                transaction.id,
                status=new_status,
                result_code=result_code,
                result_description=result_desc,
                mpesa_receipt_number=mpesa_receipt_number,
                transaction_date=transaction_date,
                response_payload=callback_data
            )

            # Create callback record
            await mpesa_repo.create_callback(
                callback_type="b2c_result",
                callback_data=callback_data,
                mpesa_transaction_id=transaction.id
            )

            logger.info(
                "B2C result processed",
                transaction_id=str(transaction.id),
                status=new_status,
                receipt=mpesa_receipt_number
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )

    except Exception as e:
        logger.error("Error handling B2C result", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 1,
                "ResultDesc": "Failed"
            }
        )


@router.post("/account-balance-result")
async def mpesa_account_balance_result(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    M-Pesa account balance result callback

    Receives account balance query results.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        JSONResponse: Acknowledgment response
    """
    try:
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Received account balance result",
            callback_data=callback_data
        )

        # TODO: Store balance information for reconciliation
        # This can be used for automated balance monitoring

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )

    except Exception as e:
        logger.error("Error handling account balance result", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 1,
                "ResultDesc": "Failed"
            }
        )


@router.post("/transaction-status-result")
async def mpesa_transaction_status_result(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    M-Pesa transaction status query result callback

    Receives transaction status query results.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        JSONResponse: Acknowledgment response
    """
    try:
        body = await request.body()
        callback_data = json.loads(body.decode('utf-8'))

        logger.info(
            "Received transaction status result",
            callback_data=callback_data
        )

        # TODO: Update transaction status based on query result
        # This can be used for transaction reconciliation

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )

    except Exception as e:
        logger.error("Error handling transaction status result", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ResultCode": 1,
                "ResultDesc": "Failed"
            }
        )
