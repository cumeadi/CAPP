"""
MMO Service Orchestrator

Orchestrates mobile money operations across multiple providers (M-Pesa, MTN MoMo, Airtel Money, etc.)
Routes payment requests to the appropriate MMO provider and handles retry logic.
"""

import asyncio
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID
import structlog

from ..models.payments import MMOProvider, Currency, Country
from ..services.mpesa_integration import MpesaService
from ..repositories.mpesa import MpesaRepository
from ..repositories.payment import PaymentRepository
from ..core.database import AsyncSessionLocal
from ..config.settings import get_settings

logger = structlog.get_logger(__name__)


class MMOPaymentRequest:
    """MMO payment request model"""
    def __init__(
        self,
        payment_id: UUID,
        provider: MMOProvider,
        phone_number: str,
        amount: Decimal,
        currency: Currency,
        country: Country,
        reference: str,
        description: str,
        transaction_type: str = "b2c"  # b2c, c2b, stk_push
    ):
        self.payment_id = payment_id
        self.provider = provider
        self.phone_number = phone_number
        self.amount = amount
        self.currency = currency
        self.country = country
        self.reference = reference
        self.description = description
        self.transaction_type = transaction_type


class MMOPaymentResult:
    """MMO payment result model"""
    def __init__(
        self,
        success: bool,
        provider: MMOProvider,
        transaction_id: Optional[str] = None,
        provider_reference: Optional[str] = None,
        status: str = "pending",
        message: str = "",
        error_code: Optional[str] = None,
        retry_possible: bool = False
    ):
        self.success = success
        self.provider = provider
        self.transaction_id = transaction_id
        self.provider_reference = provider_reference
        self.status = status
        self.message = message
        self.error_code = error_code
        self.retry_possible = retry_possible


class MMOOrchestrator:
    """
    MMO Service Orchestrator

    Routes payment requests to appropriate MMO providers:
    - M-Pesa (Kenya, Tanzania, Uganda)
    - MTN Mobile Money (Ghana, Uganda, Nigeria, etc.)
    - Airtel Money (Kenya, Uganda, Tanzania, etc.)
    - Orange Money (West Africa)

    Handles:
    - Provider routing based on country and provider
    - Retry logic for failed transactions
    - Fallback to alternative providers
    - Database persistence
    """

    def __init__(self, db_session=None):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        self.db_session = db_session

        # Initialize MMO services
        self.mpesa_service = MpesaService(db_session=db_session)
        # Future: self.mtn_service = MTNMoMoService(db_session=db_session)
        # Future: self.airtel_service = AirtelMoneyService(db_session=db_session)
        # Future: self.orange_service = OrangeMoneyService(db_session=db_session)

        # Provider availability by country
        self.provider_availability = self._initialize_provider_availability()

        # Retry configuration
        self.max_retries = 3
        self.retry_delay_seconds = 2  # Initial retry delay
        self.retry_backoff_multiplier = 2  # Exponential backoff

    def _initialize_provider_availability(self) -> Dict[Country, list]:
        """Initialize provider availability by country"""
        return {
            Country.KENYA: [MMOProvider.MPESA, MMOProvider.AIRTEL_MONEY],
            Country.TANZANIA: [MMOProvider.MPESA_TANZANIA, MMOProvider.AIRTEL_MONEY, MMOProvider.TIGO_PESA],
            Country.UGANDA: [MMOProvider.MPESA_UGANDA, MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
            Country.GHANA: [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY, MMOProvider.VODAFONE_CASH],
            Country.NIGERIA: [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
            Country.RWANDA: [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
            Country.ZAMBIA: [MMOProvider.MTN_MOBILE_MONEY, MMOProvider.AIRTEL_MONEY],
            Country.SOUTH_AFRICA: [MMOProvider.VODAFONE_CASH],
            # Add more countries as needed
        }

    async def execute_payment(
        self,
        request: MMOPaymentRequest,
        retry_on_failure: bool = True
    ) -> MMOPaymentResult:
        """
        Execute MMO payment with retry logic

        Args:
            request: MMO payment request
            retry_on_failure: Whether to retry on failure

        Returns:
            MMOPaymentResult: Payment result
        """
        self.logger.info(
            "Executing MMO payment",
            payment_id=request.payment_id,
            provider=request.provider,
            amount=request.amount,
            country=request.country
        )

        # Validate provider availability for country
        if not self._is_provider_available(request.provider, request.country):
            self.logger.warning(
                "Provider not available for country",
                provider=request.provider,
                country=request.country
            )
            return MMOPaymentResult(
                success=False,
                provider=request.provider,
                message=f"Provider {request.provider} not available in {request.country}",
                error_code="PROVIDER_NOT_AVAILABLE",
                retry_possible=False
            )

        # Execute with retry logic
        if retry_on_failure:
            return await self._execute_with_retry(request)
        else:
            return await self._execute_payment_single(request)

    async def _execute_with_retry(self, request: MMOPaymentRequest) -> MMOPaymentResult:
        """Execute payment with retry logic"""
        retry_count = 0
        retry_delay = self.retry_delay_seconds

        while retry_count <= self.max_retries:
            try:
                # Execute payment
                result = await self._execute_payment_single(request)

                if result.success:
                    self.logger.info(
                        "MMO payment successful",
                        payment_id=request.payment_id,
                        provider=request.provider,
                        transaction_id=result.transaction_id,
                        retry_count=retry_count
                    )
                    return result

                # Check if retry is possible
                if not result.retry_possible or retry_count >= self.max_retries:
                    self.logger.warning(
                        "MMO payment failed, no retry",
                        payment_id=request.payment_id,
                        provider=request.provider,
                        error_code=result.error_code,
                        retry_count=retry_count
                    )
                    return result

                # Retry with exponential backoff
                retry_count += 1
                self.logger.info(
                    "Retrying MMO payment",
                    payment_id=request.payment_id,
                    provider=request.provider,
                    retry_count=retry_count,
                    retry_delay=retry_delay
                )

                await asyncio.sleep(retry_delay)
                retry_delay *= self.retry_backoff_multiplier

            except Exception as e:
                self.logger.error(
                    "MMO payment execution error",
                    payment_id=request.payment_id,
                    provider=request.provider,
                    error=str(e),
                    retry_count=retry_count,
                    exc_info=True
                )

                if retry_count >= self.max_retries:
                    return MMOPaymentResult(
                        success=False,
                        provider=request.provider,
                        message=f"Payment failed after {retry_count} retries: {str(e)}",
                        error_code="EXECUTION_ERROR",
                        retry_possible=False
                    )

                retry_count += 1
                await asyncio.sleep(retry_delay)
                retry_delay *= self.retry_backoff_multiplier

        return MMOPaymentResult(
            success=False,
            provider=request.provider,
            message=f"Payment failed after {self.max_retries} retries",
            error_code="MAX_RETRIES_EXCEEDED",
            retry_possible=False
        )

    async def _execute_payment_single(self, request: MMOPaymentRequest) -> MMOPaymentResult:
        """Execute single payment attempt"""
        try:
            # Route to appropriate provider
            if request.provider in [MMOProvider.MPESA, MMOProvider.MPESA_TANZANIA, MMOProvider.MPESA_UGANDA]:
                return await self._execute_mpesa_payment(request)
            elif request.provider == MMOProvider.MTN_MOBILE_MONEY:
                return await self._execute_mtn_payment(request)
            elif request.provider == MMOProvider.AIRTEL_MONEY:
                return await self._execute_airtel_payment(request)
            elif request.provider == MMOProvider.ORANGE_MONEY:
                return await self._execute_orange_payment(request)
            else:
                return MMOPaymentResult(
                    success=False,
                    provider=request.provider,
                    message=f"Provider {request.provider} not implemented",
                    error_code="PROVIDER_NOT_IMPLEMENTED",
                    retry_possible=False
                )

        except Exception as e:
            self.logger.error(
                "Payment execution error",
                payment_id=request.payment_id,
                provider=request.provider,
                error=str(e),
                exc_info=True
            )
            return MMOPaymentResult(
                success=False,
                provider=request.provider,
                message=f"Payment execution failed: {str(e)}",
                error_code="EXECUTION_ERROR",
                retry_possible=True
            )

    async def _execute_mpesa_payment(self, request: MMOPaymentRequest) -> MMOPaymentResult:
        """Execute M-Pesa payment"""
        try:
            self.logger.info(
                "Executing M-Pesa payment",
                payment_id=request.payment_id,
                transaction_type=request.transaction_type,
                amount=request.amount
            )

            # Determine transaction type and execute
            if request.transaction_type == "stk_push":
                result = await self.mpesa_service.initiate_stk_push(
                    phone_number=request.phone_number,
                    amount=float(request.amount),
                    account_reference=request.reference,
                    transaction_desc=request.description
                )
            elif request.transaction_type == "b2c":
                result = await self.mpesa_service.initiate_b2c_payment(
                    phone_number=request.phone_number,
                    amount=float(request.amount),
                    reference=request.reference,
                    description=request.description
                )
            else:
                return MMOPaymentResult(
                    success=False,
                    provider=request.provider,
                    message=f"M-Pesa transaction type {request.transaction_type} not supported",
                    error_code="UNSUPPORTED_TRANSACTION_TYPE",
                    retry_possible=False
                )

            # Parse result
            if result.get("success"):
                return MMOPaymentResult(
                    success=True,
                    provider=request.provider,
                    transaction_id=result.get("checkout_request_id") or result.get("conversation_id"),
                    provider_reference=result.get("merchant_request_id") or result.get("originator_conversation_id"),
                    status="pending",
                    message="M-Pesa payment initiated successfully",
                    retry_possible=False
                )
            else:
                # Determine if retry is possible based on error code
                error_code = result.get("error_code", "UNKNOWN_ERROR")
                retry_possible = self._is_mpesa_error_retryable(error_code)

                return MMOPaymentResult(
                    success=False,
                    provider=request.provider,
                    status="failed",
                    message=result.get("message", "M-Pesa payment failed"),
                    error_code=error_code,
                    retry_possible=retry_possible
                )

        except Exception as e:
            self.logger.error(
                "M-Pesa payment error",
                payment_id=request.payment_id,
                error=str(e),
                exc_info=True
            )
            return MMOPaymentResult(
                success=False,
                provider=request.provider,
                message=f"M-Pesa payment error: {str(e)}",
                error_code="MPESA_ERROR",
                retry_possible=True
            )

    async def _execute_mtn_payment(self, request: MMOPaymentRequest) -> MMOPaymentResult:
        """Execute MTN Mobile Money payment"""
        # TODO: Implement MTN Mobile Money integration
        self.logger.warning(
            "MTN Mobile Money not yet implemented",
            payment_id=request.payment_id
        )
        return MMOPaymentResult(
            success=False,
            provider=request.provider,
            message="MTN Mobile Money integration not yet implemented",
            error_code="NOT_IMPLEMENTED",
            retry_possible=False
        )

    async def _execute_airtel_payment(self, request: MMOPaymentRequest) -> MMOPaymentResult:
        """Execute Airtel Money payment"""
        # TODO: Implement Airtel Money integration
        self.logger.warning(
            "Airtel Money not yet implemented",
            payment_id=request.payment_id
        )
        return MMOPaymentResult(
            success=False,
            provider=request.provider,
            message="Airtel Money integration not yet implemented",
            error_code="NOT_IMPLEMENTED",
            retry_possible=False
        )

    async def _execute_orange_payment(self, request: MMOPaymentRequest) -> MMOPaymentResult:
        """Execute Orange Money payment"""
        # TODO: Implement Orange Money integration
        self.logger.warning(
            "Orange Money not yet implemented",
            payment_id=request.payment_id
        )
        return MMOPaymentResult(
            success=False,
            provider=request.provider,
            message="Orange Money integration not yet implemented",
            error_code="NOT_IMPLEMENTED",
            retry_possible=False
        )

    def _is_provider_available(self, provider: MMOProvider, country: Country) -> bool:
        """Check if provider is available in country"""
        available_providers = self.provider_availability.get(country, [])
        return provider in available_providers

    def _is_mpesa_error_retryable(self, error_code: str) -> bool:
        """Determine if M-Pesa error is retryable"""
        # Non-retryable errors
        non_retryable = [
            "USER_CANCELLED",
            "INVALID_PHONE_NUMBER",
            "INVALID_ACCOUNT",
            "INSUFFICIENT_BALANCE",
            "INVALID_CREDENTIALS",
            "DUPLICATE_REQUEST"
        ]

        if error_code in non_retryable:
            return False

        # Retryable errors include network issues, timeouts, temporary failures
        return True

    async def get_provider_availability(self, country: Country) -> list:
        """Get available providers for country"""
        return self.provider_availability.get(country, [])

    async def get_recommended_provider(
        self,
        country: Country,
        amount: Decimal,
        currency: Currency
    ) -> Optional[MMOProvider]:
        """Get recommended provider for country based on amount and currency"""
        available_providers = await self.get_provider_availability(country)

        if not available_providers:
            return None

        # Simple selection logic - can be enhanced with:
        # - Provider success rates
        # - Transaction costs
        # - Processing speeds
        # - Provider availability status

        # For now, return first available provider
        # In future, this would query provider metrics and select optimal provider
        return available_providers[0]
