"""
Payment endpoints for CAPP API
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentType,
    PaymentMethod, Country, Currency, MMOProvider
)
from ...models.user import User
from ...services.payment_service import PaymentService
from ...core.database import get_db
from ...core.redis import get_redis_client
from ...api.dependencies.auth import get_current_active_user, get_optional_user

router = APIRouter()


class CreatePaymentRequest(BaseModel):
    """Request model for creating a payment"""
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
    priority_cost: bool = True
    priority_speed: bool = False
    max_delivery_time: Optional[int] = None  # in minutes
    max_fees: Optional[float] = None


class PaymentResponse(BaseModel):
    """Response model for payment operations"""
    success: bool
    payment_id: UUID
    status: PaymentStatus
    message: str
    reference_id: str
    amount: float
    fees: float
    total_cost: float
    exchange_rate: Optional[float] = None
    estimated_delivery_time: Optional[int] = None
    transaction_hash: Optional[str] = None
    error_code: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    """Response model for payment status"""
    payment_id: UUID
    reference_id: str
    status: PaymentStatus
    amount: float
    fees: float
    total_cost: float
    exchange_rate: Optional[float] = None
    estimated_delivery_time: Optional[int] = None
    actual_delivery_time: Optional[int] = None
    transaction_hash: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    payment_service: PaymentService = Depends(),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new cross-border payment

    This endpoint initiates a cross-border payment with route optimization
    and agent-based processing.

    **Authentication required**: Bearer token
    """
    try:
        # Create payment object
        payment = CrossBorderPayment(
            reference_id=request.reference_id,
            payment_type=request.payment_type,
            payment_method=request.payment_method,
            amount=request.amount,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            sender={
                "name": request.sender_name,
                "phone_number": request.sender_phone,
                "country": request.sender_country
            },
            recipient={
                "name": request.recipient_name,
                "phone_number": request.recipient_phone,
                "country": request.recipient_country
            },
            description=request.description,
            preferences={
                "prioritize_cost": request.priority_cost,
                "prioritize_speed": request.priority_speed,
                "max_delivery_time": request.max_delivery_time,
                "max_fees": request.max_fees
            }
        )
        
        # Process payment
        result = await payment_service.process_payment(payment)
        
        return PaymentResponse(
            success=result.success,
            payment_id=result.payment_id,
            status=result.status,
            message=result.message,
            reference_id=payment.reference_id,
            amount=float(payment.amount),
            fees=float(payment.fees),
            total_cost=float(payment.total_cost),
            exchange_rate=float(result.exchange_rate_used) if result.exchange_rate_used else None,
            estimated_delivery_time=result.estimated_delivery_time,
            transaction_hash=result.transaction_hash,
            error_code=result.error_code
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}"
        )


@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: UUID,
    payment_service: PaymentService = Depends(),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the status of a payment

    Returns detailed information about the payment including current status,
    fees, exchange rate, and delivery time.

    **Authentication required**: Bearer token
    """
    try:
        payment = await payment_service.get_payment(payment_id)
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        return PaymentStatusResponse(
            payment_id=payment.payment_id,
            reference_id=payment.reference_id,
            status=payment.status,
            amount=float(payment.amount),
            fees=float(payment.fees),
            total_cost=float(payment.total_cost),
            exchange_rate=float(payment.exchange_rate) if payment.exchange_rate else None,
            estimated_delivery_time=payment.selected_route.estimated_delivery_time if payment.selected_route else None,
            actual_delivery_time=None,  # Would be calculated from completed_at - created_at
            transaction_hash=payment.blockchain_tx_hash,
            created_at=payment.created_at.isoformat(),
            updated_at=payment.updated_at.isoformat(),
            completed_at=payment.completed_at.isoformat() if payment.completed_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment status: {str(e)}"
        )


@router.post("/{payment_id}/cancel")
async def cancel_payment(
    payment_id: UUID,
    payment_service: PaymentService = Depends(),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a payment

    Only payments in PENDING or PROCESSING status can be cancelled.

    **Authentication required**: Bearer token
    """
    try:
        result = await payment_service.cancel_payment(payment_id)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return {"message": "Payment cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel payment: {str(e)}"
        )


@router.get("/corridors/supported")
async def get_supported_corridors():
    """
    Get list of supported payment corridors
    
    Returns all country pairs that support cross-border payments.
    """
    # This would be populated from actual corridor data
    supported_corridors = [
        {
            "from_country": "KE",
            "to_country": "UG",
            "from_currency": "KES",
            "to_currency": "UGX",
            "estimated_delivery_time": 5,
            "min_amount": 1.0,
            "max_amount": 10000.0,
            "fees_percentage": 0.025
        },
        {
            "from_country": "NG",
            "to_country": "GH",
            "from_currency": "NGN",
            "to_currency": "GHS",
            "estimated_delivery_time": 15,
            "min_amount": 1.0,
            "max_amount": 5000.0,
            "fees_percentage": 0.03
        },
        {
            "from_country": "ZA",
            "to_country": "BW",
            "from_currency": "ZAR",
            "to_currency": "BWP",
            "estimated_delivery_time": 10,
            "min_amount": 1.0,
            "max_amount": 15000.0,
            "fees_percentage": 0.02
        }
    ]
    
    return {"corridors": supported_corridors}


@router.get("/rates/{from_currency}/{to_currency}")
async def get_exchange_rate(
    from_currency: Currency,
    to_currency: Currency
):
    """
    Get current exchange rate for currency pair
    
    Returns the current exchange rate and any applicable fees.
    """
    try:
        # This would integrate with actual exchange rate service
        # For now, return mock data
        rates = {
            ("KES", "UGX"): {"rate": 0.025, "fees": 2.50},
            ("NGN", "GHS"): {"rate": 0.012, "fees": 3.00},
            ("ZAR", "BWP"): {"rate": 0.68, "fees": 5.00},
        }
        
        rate_info = rates.get((from_currency, to_currency))
        
        if not rate_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exchange rate not available for {from_currency} to {to_currency}"
            )
        
        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": rate_info["rate"],
            "fees": rate_info["fees"],
            "last_updated": "2024-01-01T00:00:00Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get exchange rate: {str(e)}"
        )


@router.get("/mmo/providers")
async def get_mmo_providers():
    """
    Get list of supported Mobile Money Operators
    
    Returns all MMO providers and their supported countries.
    """
    mmo_providers = [
        {
            "provider": "mpesa",
            "name": "M-Pesa",
            "countries": ["KE", "TZ", "UG"],
            "supported_currencies": ["KES", "TZS", "UGX"],
            "status": "active"
        },
        {
            "provider": "orange_money",
            "name": "Orange Money",
            "countries": ["SN", "CI", "BF", "ML", "NE", "TG", "BJ", "GN", "SL", "LR", "GM", "GW", "CV"],
            "supported_currencies": ["XOF"],
            "status": "active"
        },
        {
            "provider": "mtn_mobile_money",
            "name": "MTN Mobile Money",
            "countries": ["GH", "UG", "RW", "BI", "ZM", "MW", "MZ", "AO", "NA", "ZW"],
            "supported_currencies": ["GHS", "UGX", "RWF", "BIF", "ZMW", "MWK", "MZN", "AOA", "NAD", "ZWL"],
            "status": "active"
        },
        {
            "provider": "airtel_money",
            "name": "Airtel Money",
            "countries": ["UG", "RW", "BI", "ZM", "MW", "MZ", "AO", "NA", "ZW"],
            "supported_currencies": ["UGX", "RWF", "BIF", "ZMW", "MWK", "MZN", "AOA", "NAD", "ZWL"],
            "status": "active"
        }
    ]
    
    return {"providers": mmo_providers}


@router.get("/limits")
async def get_payment_limits():
    """
    Get payment limits and restrictions
    
    Returns current limits for different payment types and corridors.
    """
    limits = {
        "daily_limits": {
            "personal_remittance": 10000.0,
            "business_payment": 50000.0,
            "bulk_disbursement": 100000.0
        },
        "transaction_limits": {
            "min_amount": 1.0,
            "max_amount": 10000.0
        },
        "currency_limits": {
            "NGN": {"min": 100, "max": 500000},
            "KES": {"min": 10, "max": 1000000},
            "GHS": {"min": 1, "max": 50000},
            "UGX": {"min": 1000, "max": 50000000}
        }
    }
    
    return limits 