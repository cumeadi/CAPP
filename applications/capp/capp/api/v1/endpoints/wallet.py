
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field

from applications.capp.capp.services.yield_service import YieldService
from applications.capp.capp.api.dependencies.auth import get_current_active_user
from applications.capp.capp.models.user import User
from applications.capp.capp.config.settings import get_settings

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


# --- HIFI Request/Response Models ---

class HifiDepositRequest(BaseModel):
    """Request to initiate a HIFI pay-in (deposit local currency)"""
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    amount: Decimal = Field(..., gt=0, description="Amount in local currency")
    payment_method: str = Field(..., pattern="^(bank_transfer|mobile_money)$")
    # KYC fields
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: Optional[str] = None  # YYYY-MM-DD
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    # Address
    address_line1: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    # Nigeria-specific
    additional_id_type: Optional[str] = None
    additional_id_number: Optional[str] = None


class HifiWithdrawRequest(BaseModel):
    """Request to initiate a HIFI pay-out (withdraw to local currency)"""
    country_code: str = Field(..., min_length=2, max_length=2)
    amount: Decimal = Field(..., gt=0, description="Amount in local currency")
    payment_method: str = Field(..., pattern="^(bank_transfer|mobile_money)$")
    # Recipient info
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    additional_id_type: Optional[str] = None
    additional_id_number: Optional[str] = None
    # Bank details (for bank_transfer)
    bank_account_number: Optional[str] = None
    bank_code: Optional[str] = None
    # Mobile money details (for mobile_money)
    mobile_money_number: Optional[str] = None


class HifiTransactionResponse(BaseModel):
    """Response after initiating a HIFI transaction"""
    transaction_id: str
    status: str
    direction: str
    amount: str
    currency: str
    payment_method: str
    country_code: str
    estimated_delivery: Optional[str] = None
    message: str


class HifiCorridorResponse(BaseModel):
    """Corridor info for the frontend"""
    country_code: str
    country_name: str
    currency: str
    supports_payin: bool
    supports_payout: bool
    payment_methods: List[str]
    requires_additional_id: bool

@router.get("/stats")
async def get_wallet_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get wallet statistics including yield and hot wallet balances.
    """
    try:
        service = YieldService()
        # For MVP/Demo, we use a fixed wallet address or the user's mapped address if available
        # In a real system, we'd map current_user.id to their on-chain address(es) managed by CAPP
        # passing "external_client" to simulate a user wallet
        stats = await service.get_total_treasury_balance(wallet_address="external_client")
        
        # Map response to what frontend expects
        # Frontend API expects:
        # total_value_usd: number;
        # hot_wallet_balance: number;
        # yield_balance: number;
        # apy: number;
        # is_sweeping: boolean;
        
        breakdown = stats.get("breakdown", {})
        usdc_stats = breakdown.get("USDC", {})
        apt_stats = breakdown.get("APT", {})
        
        # HIFI corridor info
        hifi_info = {"enabled": False, "corridor_count": 0}
        settings = get_settings()
        if settings.HIFI_ENABLED:
            from packages.integrations.hifi.country_config import HIFI_ALL_CORRIDORS
            allowed = settings.HIFI_ALLOWED_COUNTRIES
            count = len(HIFI_ALL_CORRIDORS) if not allowed else sum(1 for c in HIFI_ALL_CORRIDORS if c in allowed)
            hifi_info = {"enabled": True, "corridor_count": count, "beta": settings.HIFI_BETA_MODE}

        return {
            "total_value_usd": stats.get("total_usd_value", 0),
            "hot_wallet_balance": usdc_stats.get("hot", 0),
            "yield_balance": usdc_stats.get("yielding", 0),
            "aptos_balance": apt_stats.get("total", 0),
            "apy": 4.5, # Mock APY
            "is_sweeping": usdc_stats.get("yielding", 0) > 0,
            "hifi": hifi_info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hifi/corridors", response_model=List[HifiCorridorResponse])
async def get_hifi_corridors(
    current_user: User = Depends(get_current_active_user)
):
    """Get supported HIFI Africa Rail corridors."""
    settings = get_settings()
    if not settings.HIFI_ENABLED:
        raise HTTPException(status_code=404, detail="HIFI Africa Rail is not enabled")

    from packages.integrations.hifi.country_config import (
        HIFI_ALL_CORRIDORS,
        requires_additional_id,
    )

    COUNTRY_NAMES = {
        "BJ": "Benin", "BW": "Botswana", "CM": "Cameroon", "CI": "Côte d'Ivoire",
        "MW": "Malawi", "NG": "Nigeria", "TZ": "Tanzania", "TG": "Togo",
        "UG": "Uganda", "ZM": "Zambia", "BF": "Burkina Faso", "KE": "Kenya",
        "ML": "Mali", "SN": "Senegal", "ZA": "South Africa",
    }

    corridors = []
    allowed = settings.HIFI_ALLOWED_COUNTRIES

    for code, info in HIFI_ALL_CORRIDORS.items():
        if allowed and code not in allowed:
            continue
        methods = []
        if info.supports_payin:
            methods.extend(["bank_transfer", "mobile_money"])
        else:
            methods.extend(["bank_transfer", "mobile_money"])

        corridors.append(HifiCorridorResponse(
            country_code=code,
            country_name=COUNTRY_NAMES.get(code, code),
            currency=info.currency,
            supports_payin=info.supports_payin,
            supports_payout=info.supports_payout,
            payment_methods=methods,
            requires_additional_id=requires_additional_id(code),
        ))

    return corridors


@router.post("/hifi/deposit", response_model=HifiTransactionResponse)
async def initiate_hifi_deposit(
    request: HifiDepositRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Initiate a HIFI pay-in (local currency deposit)."""
    settings = get_settings()
    if not settings.HIFI_ENABLED:
        raise HTTPException(status_code=404, detail="HIFI Africa Rail is not enabled")

    from packages.integrations.hifi.country_config import (
        get_corridor, supports_payin, requires_additional_id,
    )
    from packages.integrations.hifi.config import HifiConfig
    from packages.integrations.hifi.adapter import HifiAfricaRailAdapter
    from packages.integrations.hifi.exceptions import (
        HifiIntegrationException, HifiKYCException, HifiBetaLimitExceededException,
    )

    # Validate corridor supports pay-in
    corridor = get_corridor(request.country_code)
    if not corridor or not supports_payin(request.country_code):
        raise HTTPException(status_code=400, detail=f"Pay-in not supported for country {request.country_code}")

    # Allowed country check
    if settings.HIFI_ALLOWED_COUNTRIES and request.country_code not in settings.HIFI_ALLOWED_COUNTRIES:
        raise HTTPException(status_code=400, detail=f"Country {request.country_code} is not in the allowed list")

    # Beta limit check
    if settings.HIFI_BETA_MODE and request.amount > Decimal(str(settings.HIFI_MAX_TRANSACTION_AMOUNT)):
        raise HTTPException(
            status_code=400,
            detail=f"Amount exceeds beta limit of {settings.HIFI_MAX_TRANSACTION_AMOUNT} {corridor.currency}",
        )

    # Nigeria additional ID check
    if requires_additional_id(request.country_code):
        if not request.additional_id_type or not request.additional_id_number:
            raise HTTPException(status_code=400, detail="Nigeria requires additional_id_type and additional_id_number")

    try:
        config = HifiConfig(
            api_key=settings.HIFI_API_KEY,
            api_secret=settings.HIFI_API_SECRET,
            base_url=settings.HIFI_BASE_URL,
            enabled=settings.HIFI_ENABLED,
            beta_mode=settings.HIFI_BETA_MODE,
            max_transaction_amount=Decimal(str(settings.HIFI_MAX_TRANSACTION_AMOUNT)),
            allowed_countries=settings.HIFI_ALLOWED_COUNTRIES,
            fallback_enabled=settings.HIFI_FALLBACK_ENABLED,
        )
        adapter = HifiAfricaRailAdapter(config=config)

        result = await adapter.execute_directed_transfer(
            direction="payin",
            amount=request.amount,
            currency=corridor.currency,
            country_code=request.country_code,
            payment_method=request.payment_method,
            sender_info={
                "first_name": request.first_name,
                "last_name": request.last_name,
                "email": request.email,
                "phone": request.phone,
                "date_of_birth": request.date_of_birth,
                "id_type": request.id_type,
                "id_number": request.id_number,
                "address_line1": request.address_line1,
                "city": request.city,
                "postal_code": request.postal_code,
                "country": request.country_code,
                "additional_id_type": request.additional_id_type,
                "additional_id_number": request.additional_id_number,
            },
            recipient_info=None,
        )

        return HifiTransactionResponse(
            transaction_id=result.get("transaction_id", ""),
            status=result.get("status", "pending"),
            direction="payin",
            amount=str(request.amount),
            currency=corridor.currency,
            payment_method=request.payment_method,
            country_code=request.country_code,
            estimated_delivery=result.get("estimated_delivery"),
            message="Deposit initiated successfully",
        )

    except HifiKYCException as e:
        raise HTTPException(status_code=422, detail=f"KYC validation failed: {e.message}")
    except HifiBetaLimitExceededException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HifiIntegrationException as e:
        logger.error("HIFI deposit failed", error=str(e), country=request.country_code)
        raise HTTPException(status_code=502, detail="HIFI service error. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error during HIFI deposit", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/hifi/withdraw", response_model=HifiTransactionResponse)
async def initiate_hifi_withdraw(
    request: HifiWithdrawRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Initiate a HIFI pay-out (withdraw to local currency)."""
    settings = get_settings()
    if not settings.HIFI_ENABLED:
        raise HTTPException(status_code=404, detail="HIFI Africa Rail is not enabled")

    from packages.integrations.hifi.country_config import (
        get_corridor, supports_payout, requires_additional_id,
    )
    from packages.integrations.hifi.config import HifiConfig
    from packages.integrations.hifi.adapter import HifiAfricaRailAdapter
    from packages.integrations.hifi.exceptions import (
        HifiIntegrationException, HifiKYCException, HifiBetaLimitExceededException,
    )

    # Validate corridor supports pay-out
    corridor = get_corridor(request.country_code)
    if not corridor or not supports_payout(request.country_code):
        raise HTTPException(status_code=400, detail=f"Pay-out not supported for country {request.country_code}")

    if settings.HIFI_ALLOWED_COUNTRIES and request.country_code not in settings.HIFI_ALLOWED_COUNTRIES:
        raise HTTPException(status_code=400, detail=f"Country {request.country_code} is not in the allowed list")

    if settings.HIFI_BETA_MODE and request.amount > Decimal(str(settings.HIFI_MAX_TRANSACTION_AMOUNT)):
        raise HTTPException(
            status_code=400,
            detail=f"Amount exceeds beta limit of {settings.HIFI_MAX_TRANSACTION_AMOUNT} {corridor.currency}",
        )

    if requires_additional_id(request.country_code):
        if not request.additional_id_type or not request.additional_id_number:
            raise HTTPException(status_code=400, detail="Nigeria requires additional_id_type and additional_id_number")

    try:
        config = HifiConfig(
            api_key=settings.HIFI_API_KEY,
            api_secret=settings.HIFI_API_SECRET,
            base_url=settings.HIFI_BASE_URL,
            enabled=settings.HIFI_ENABLED,
            beta_mode=settings.HIFI_BETA_MODE,
            max_transaction_amount=Decimal(str(settings.HIFI_MAX_TRANSACTION_AMOUNT)),
            allowed_countries=settings.HIFI_ALLOWED_COUNTRIES,
            fallback_enabled=settings.HIFI_FALLBACK_ENABLED,
        )
        adapter = HifiAfricaRailAdapter(config=config)

        result = await adapter.execute_directed_transfer(
            direction="payout",
            amount=request.amount,
            currency=corridor.currency,
            country_code=request.country_code,
            payment_method=request.payment_method,
            sender_info=None,
            recipient_info={
                "first_name": request.first_name,
                "last_name": request.last_name,
                "email": request.email,
                "phone": request.phone,
                "date_of_birth": request.date_of_birth,
                "id_type": request.id_type,
                "id_number": request.id_number,
                "address_line1": request.address_line1,
                "city": request.city,
                "postal_code": request.postal_code,
                "country": request.country_code,
                "additional_id_type": request.additional_id_type,
                "additional_id_number": request.additional_id_number,
                "bank_account_number": request.bank_account_number,
                "bank_code": request.bank_code,
                "mobile_money_number": request.mobile_money_number,
            },
        )

        return HifiTransactionResponse(
            transaction_id=result.get("transaction_id", ""),
            status=result.get("status", "pending"),
            direction="payout",
            amount=str(request.amount),
            currency=corridor.currency,
            payment_method=request.payment_method,
            country_code=request.country_code,
            estimated_delivery=result.get("estimated_delivery"),
            message="Withdrawal initiated successfully",
        )

    except HifiKYCException as e:
        raise HTTPException(status_code=422, detail=f"KYC validation failed: {e.message}")
    except HifiBetaLimitExceededException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HifiIntegrationException as e:
        logger.error("HIFI withdrawal failed", error=str(e), country=request.country_code)
        raise HTTPException(status_code=502, detail="HIFI service error. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error during HIFI withdrawal", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
