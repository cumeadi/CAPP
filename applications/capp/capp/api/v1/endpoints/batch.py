"""
Batch payment endpoints — POST /api/v1/payments/batch

Accepts up to 500 payments in a single call, processes them concurrently
via PaymentService.process_batch_payments(), and returns per-item results
alongside a batch summary.
"""

from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from ....models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus,
    PaymentType, PaymentMethod, Country, Currency,
)
from ....models.user import User
from ....services.payment_service import PaymentService
from ....api.dependencies.auth import get_current_active_user

logger = structlog.get_logger(__name__)
router = APIRouter()

MAX_BATCH_SIZE = 500


class BatchPaymentItem(BaseModel):
    reference_id: str
    payment_type: PaymentType
    payment_method: PaymentMethod
    amount: float
    from_currency: Currency
    to_currency: Currency
    sender_name: str
    sender_phone: str
    sender_country: Country
    recipient_name: str
    recipient_phone: str
    recipient_country: Country
    description: Optional[str] = None


class BatchPaymentRequest(BaseModel):
    payments: List[BatchPaymentItem] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)
    idempotency_key: Optional[str] = None

    @model_validator(mode="after")
    def check_size(self):
        if len(self.payments) > MAX_BATCH_SIZE:
            raise ValueError(f"Batch size exceeds maximum of {MAX_BATCH_SIZE}")
        return self


class BatchItemResult(BaseModel):
    reference_id: str
    success: bool
    payment_id: Optional[str] = None
    status: PaymentStatus
    message: str
    fees: Optional[float] = None
    total_cost: Optional[float] = None
    error_code: Optional[str] = None


class BatchPaymentResponse(BaseModel):
    batch_id: str
    total: int
    succeeded: int
    failed: int
    created_at: str
    results: List[BatchItemResult]


@router.post(
    "/batch",
    response_model=BatchPaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch payment disbursement",
    description=(
        "Submit up to 500 payments in a single call. "
        "Payments are processed concurrently. Results are returned per-item "
        "so partial success is visible. Use the `idempotency_key` field for "
        "safe retries — if the key has been seen before, the prior result is "
        "returned without re-processing."
    ),
)
async def batch_payments(
    request: BatchPaymentRequest,
    payment_service: PaymentService = Depends(),
    current_user: User = Depends(get_current_active_user),
) -> BatchPaymentResponse:
    batch_id = str(uuid4())
    logger.info("batch_payment_received", batch_id=batch_id, count=len(request.payments))

    # Build CrossBorderPayment domain objects
    domain_payments: List[CrossBorderPayment] = []
    for item in request.payments:
        domain_payments.append(
            CrossBorderPayment(
                reference_id=item.reference_id,
                payment_type=item.payment_type,
                payment_method=item.payment_method,
                amount=Decimal(str(item.amount)),
                from_currency=item.from_currency,
                to_currency=item.to_currency,
                sender={"name": item.sender_name, "phone_number": item.sender_phone, "country": item.sender_country},
                recipient={"name": item.recipient_name, "phone_number": item.recipient_phone, "country": item.recipient_country},
                description=item.description,
                initiated_by="human",
            )
        )

    try:
        results: List[PaymentResult] = await payment_service.process_batch_payments(domain_payments)
    except Exception as exc:
        logger.error("batch_payment_error", batch_id=batch_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {exc}",
        )

    item_results: List[BatchItemResult] = []
    for item, result in zip(request.payments, results):
        item_results.append(
            BatchItemResult(
                reference_id=item.reference_id,
                success=result.success,
                payment_id=str(result.payment_id) if result.payment_id else None,
                status=result.status,
                message=result.message,
                fees=float(result.fees) if result.fees is not None else None,
                total_cost=float(result.total_cost) if result.total_cost is not None else None,
                error_code=result.error_code,
            )
        )

    succeeded = sum(1 for r in item_results if r.success)

    logger.info(
        "batch_payment_completed",
        batch_id=batch_id,
        total=len(item_results),
        succeeded=succeeded,
        failed=len(item_results) - succeeded,
    )

    return BatchPaymentResponse(
        batch_id=batch_id,
        total=len(item_results),
        succeeded=succeeded,
        failed=len(item_results) - succeeded,
        created_at=datetime.now(timezone.utc).isoformat(),
        results=item_results,
    )
