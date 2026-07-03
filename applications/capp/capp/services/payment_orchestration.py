"""
Payment Orchestration Service for CAPP

Coordinates the complete end-to-end payment processing workflow including
route optimization, compliance validation, liquidity management, and settlement.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import structlog

from capp.models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    PaymentType, PaymentMethod, Country, Currency, MMOProvider,
    RailProvider, TransactionDirection,
)
from capp.agents.base import agent_registry
from capp.agents.routing.route_optimization_agent import RouteOptimizationAgent, RouteOptimizationConfig
from capp.services.payment_service import PaymentService
from capp.services.exchange_rates import ExchangeRateService
from capp.services.compliance import ComplianceService
from capp.services.mmo_availability import MMOAvailabilityService
from capp.services.metrics import MetricsCollector
from capp.services.yield_service import YieldService
from capp.core.redis import get_cache
from capp.config.settings import get_settings

logger = structlog.get_logger(__name__)


class PaymentOrchestrationService:
    """
    Payment Orchestration Service
    
    Orchestrates the complete payment processing workflow:
    1. Payment validation and initialization
    2. Route optimization and selection
    3. Compliance validation
    4. Liquidity availability check
    5. Exchange rate locking
    6. MMO execution
    7. Blockchain settlement
    8. Confirmation and notifications
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
        
        # Core services
        self.payment_service = PaymentService()
        self.exchange_rate_service = ExchangeRateService()
        self.compliance_service = ComplianceService()
        self.mmo_availability_service = MMOAvailabilityService()
        self.metrics_collector = MetricsCollector()
        self.yield_service = YieldService()

        # HIFI Africa Rail (conditionally loaded)
        self.hifi_adapter = None
        if self.settings.HIFI_ENABLED:
            self._initialize_hifi()

        # Initialize agents
        self._initialize_agents()
    
    def _initialize_hifi(self):
        """Initialize HIFI Africa Rail adapter with circuit breaker"""
        try:
            from packages.integrations.hifi.adapter import HifiAfricaRailAdapter
            from packages.integrations.hifi.config import HifiConfig
            from capp.adapters.base import AdapterConfig
            from capp.services.circuit_breaker import get_circuit_breaker

            hifi_config = HifiConfig(
                api_key=self.settings.HIFI_API_KEY,
                api_secret=self.settings.HIFI_API_SECRET,
                base_url=self.settings.HIFI_BASE_URL,
                enabled=self.settings.HIFI_ENABLED,
                beta_mode=self.settings.HIFI_BETA_MODE,
                max_transaction_amount=Decimal(str(self.settings.HIFI_MAX_TRANSACTION_AMOUNT)),
                allowed_countries=self.settings.HIFI_ALLOWED_COUNTRIES,
                fallback_enabled=self.settings.HIFI_FALLBACK_ENABLED,
            )
            adapter_config = AdapterConfig(
                name="hifi_africa_rail",
                network="hifi",
                enabled=True,
                metadata={"beta": True},
            )
            self.hifi_adapter = HifiAfricaRailAdapter(adapter_config, hifi_config)
            # Lower threshold for beta: open after 3 failures, recover after 5 minutes
            self.hifi_circuit_breaker = get_circuit_breaker("hifi_africa_rail", threshold=3, timeout=300)
            self.logger.info("HIFI Africa Rail adapter initialized")
        except Exception as e:
            self.logger.error("Failed to initialize HIFI adapter", error=str(e))
            self.hifi_adapter = None

    def _initialize_agents(self):
        """Initialize all required agents"""
        try:
            # Register route optimization agent
            route_config = RouteOptimizationConfig()
            agent_registry.register_agent_type("route_optimization", RouteOptimizationAgent)

            self.logger.info("Payment orchestration agents initialized")

        except Exception as e:
            self.logger.error("Failed to initialize agents", error=str(e))
            raise
    
    async def process_payment_flow(self, payment_request: Dict[str, Any]) -> PaymentResult:
        """
        Complete end-to-end payment processing
        
        Args:
            payment_request: Payment request data
            
        Returns:
            PaymentResult: Complete payment processing result
        """
        start_time = datetime.now(timezone.utc)
        payment = None
        
        try:
            self.logger.info(
                "Starting payment orchestration",
                request_id=payment_request.get("reference_id"),
                amount=payment_request.get("amount"),
                from_country=payment_request.get("sender_country"),
                to_country=payment_request.get("recipient_country")
            )
            
            # Step 1: Create and validate payment
            payment = await self._create_payment(payment_request)
            if not payment:
                return PaymentResult(
                    success=False,
                    payment_id=str(uuid4()),
                    status=PaymentStatus.FAILED,
                    message="Failed to create payment",
                    error_code="PAYMENT_CREATION_FAILED"
                )
            
            # Step 2: Route optimization
            route_result = await self._optimize_route(payment)
            if not route_result.success:
                return await self._handle_payment_failure(payment, "Route optimization failed")
            
            # Step 3: Compliance validation
            compliance_result = await self._validate_compliance(payment)
            if not compliance_result.success:
                # Check if we need to pause for review instead of failing
                if compliance_result.status == PaymentStatus.COMPLIANCE_REVIEW:
                    self.logger.info("Payment paused for Compliance Review", payment_id=payment.payment_id)
                    payment.update_status(PaymentStatus.COMPLIANCE_REVIEW)
                    # In a real async system, we would stop here and resume later.
                    # For this demo flow, we return early.
                    return compliance_result
                    
                return await self._handle_payment_failure(payment, "Compliance validation failed")
            
            # Step 4: Liquidity check (Smart Sweep Integration)
            liquidity_result = await self._check_liquidity(payment)
            if not liquidity_result.success:
                 # Check if we are unwinding yield
                if liquidity_result.status == PaymentStatus.YIELD_UNWINDING:
                    self.logger.info("Payment paused for Yield Unwinding", payment_id=payment.payment_id)
                    payment.update_status(PaymentStatus.YIELD_UNWINDING)
                    # The system would resume after unwinding.
                    # We can optionally sleep loop here or return "Processing/Pending"
                    # For demo purposes, we will treat it as a successful "pause" state
                    # But since the request_liquidity mock includes the sleep, we can assume it's ready now?
                    # Actually, yield_service.request_liquidity() is async and waits. 
                    # If it returned True, we have funds. If False, we failed.
                    # Let's revisit _check_liquidity logic below.
                    pass
                else:
                    return await self._handle_payment_failure(payment, "Insufficient liquidity")
            
            # Step 5: Exchange rate locking
            rate_result = await self._lock_exchange_rate(payment)
            if not rate_result.success:
                return await self._handle_payment_failure(payment, "Exchange rate locking failed")
            
            # Step 6: MMO execution
            mmo_result = await self._execute_mmo_payment(payment)
            if not mmo_result.success:
                return await self._handle_payment_failure(payment, "MMO execution failed")
            
            # Step 7: Blockchain settlement
            settlement_result = await self._settle_payment(payment)
            if not settlement_result.success:
                return await self._handle_payment_failure(payment, "Blockchain settlement failed")
            
            # Step 8: Final confirmation
            confirmation_result = await self._confirm_payment(payment)
            if not confirmation_result.success:
                return await self._handle_payment_failure(payment, "Payment confirmation failed")
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Record metrics
            await self._record_payment_metrics(payment, processing_time, True)
            
            self.logger.info(
                "Payment orchestration completed successfully",
                payment_id=payment.payment_id,
                processing_time=processing_time,
                amount=payment.amount  # NOTE: total_cost was a bug (no such attribute)
            )
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.COMPLETED,
                message="Payment processed successfully",
                transaction_hash=settlement_result.transaction_hash,
                estimated_delivery_time=payment.selected_route.estimated_delivery_time if payment.selected_route else None,
                fees_charged=payment.selected_route.fees if payment.selected_route else None,  # NOTE: payment has no fees field
                exchange_rate_used=payment.exchange_rate
            )
            
        except Exception as e:
            self.logger.error(
                "Payment orchestration failed",
                payment_id=payment.payment_id if payment else None,
                error=str(e),
                exc_info=True
            )
            
            if payment:
                await self._handle_payment_failure(payment, f"Orchestration error: {str(e)}")
            
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id if payment else "",
                status=PaymentStatus.FAILED,
                message=f"Payment orchestration failed: {str(e)}",
                error_code="ORCHESTRATION_ERROR"
            )
    
    async def _create_payment(self, payment_request: Dict[str, Any]) -> Optional[CrossBorderPayment]:
        """Create and validate payment object"""
        try:
            # Create payment object from request
            payment = CrossBorderPayment(
                reference_id=payment_request["reference_id"],
                payment_type=PaymentType(payment_request.get("payment_type", "personal_remittance")),
                payment_method=PaymentMethod(payment_request.get("payment_method", "mobile_money")),
                amount=Decimal(str(payment_request["amount"])),
                from_currency=Currency(payment_request["from_currency"]),
                to_currency=Currency(payment_request["to_currency"]),
                sender={
                    "name": payment_request["sender_name"],
                    "phone_number": payment_request["sender_phone"],
                    "country": Country(payment_request["sender_country"])
                },
                recipient={
                    "name": payment_request["recipient_name"],
                    "phone_number": payment_request["recipient_phone"],
                    "country": Country(payment_request["recipient_country"])
                },
                description=payment_request.get("description"),
                preferences={
                    "prioritize_cost": payment_request.get("priority_cost", True),
                    "prioritize_speed": payment_request.get("priority_speed", False),
                    "max_delivery_time": payment_request.get("max_delivery_time"),
                    "max_fees": payment_request.get("max_fees")
                }
            )
            
            # Validate payment
            if not await self._validate_payment(payment):
                return None
            
            self.logger.info("Payment created successfully", payment_id=payment.payment_id)
            return payment
            
        except Exception as e:
            self.logger.error("Failed to create payment", error=str(e))
            return None
    
    async def _validate_payment(self, payment: CrossBorderPayment) -> bool:
        """Validate payment requirements"""
        try:
            # Check amount limits
            if payment.amount < self.settings.MIN_PAYMENT_AMOUNT:
                self.logger.warning("Payment amount below minimum", amount=payment.amount)
                return False
            
            if payment.amount > self.settings.MAX_PAYMENT_AMOUNT:
                self.logger.warning("Payment amount above maximum", amount=payment.amount)
                return False
            
            # Check if corridor is supported
            if not await self._is_corridor_supported(payment.sender.country, payment.recipient.country):
                self.logger.warning("Payment corridor not supported", 
                                  from_country=payment.sender.country, 
                                  to_country=payment.recipient.country)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Payment validation failed", error=str(e))
            return False
    
    async def _is_corridor_supported(self, from_country: Country, to_country: Country) -> bool:
        """Check if payment corridor is supported"""
        # Mock corridor support - in real implementation, this would check against supported corridors
        supported_corridors = [
            (Country.KENYA, Country.UGANDA),
            (Country.NIGERIA, Country.GHANA),
            (Country.NIGERIA, Country.KENYA),  # Add Nigeria to Kenya corridor
            (Country.SOUTH_AFRICA, Country.BOTSWANA),
            (Country.KENYA, Country.TANZANIA),
            (Country.UGANDA, Country.KENYA),
            (Country.GHANA, Country.NIGERIA),
            (Country.BOTSWANA, Country.SOUTH_AFRICA),
            (Country.TANZANIA, Country.KENYA),
        ]
        
        return (from_country, to_country) in supported_corridors
    
    async def _optimize_route(self, payment: CrossBorderPayment) -> PaymentResult:
        """Optimize payment route"""
        try:
            # Get route optimization agent
            route_agents = agent_registry.get_agents_by_type("route_optimization")
            if not route_agents:
                route_config = RouteOptimizationConfig()
                route_agent = RouteOptimizationAgent(route_config)
                await agent_registry.create_agent("route_optimization", route_config)
                route_agents = [route_agent]
            
            route_agent = route_agents[0]
            
            # Process payment with route optimization
            result = await route_agent.process_payment_with_retry(payment)
            
            if result.success:
                self.logger.info("Route optimization completed", payment_id=payment.payment_id)
            
            return result
            
        except Exception as e:
            self.logger.error("Route optimization failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Route optimization failed: {str(e)}",
                error_code="ROUTE_OPTIMIZATION_ERROR"
            )
    
    async def _validate_compliance(self, payment: CrossBorderPayment) -> PaymentResult:
        """Validate compliance requirements"""
        try:
            # Check KYC compliance
            kyc_result = await self.compliance_service.check_kyc_compliance(
                payment.sender.country,
                payment.recipient.country,
                float(payment.amount)
            )
            
            if not kyc_result.is_compliant:
                # Check for Shield Review
                if kyc_result.risk_level in ["medium", "high"]:
                     return PaymentResult(
                        success=False, # Temporarily False to stop flow
                        payment_id=payment.payment_id,
                        status=PaymentStatus.COMPLIANCE_REVIEW,
                        message="Flagged for Institutional Review",
                        error_code="COMPLIANCE_REVIEW_REQUIRED"
                    )

                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=f"KYC compliance failed: {', '.join(kyc_result.violations)}",
                    error_code="COMPLIANCE_ERROR"
                )
            
            # Check sanctions
            sanctions_result = await self.compliance_service.check_sanctions(
                payment.sender.country,
                payment.recipient.country
            )
            
            if not sanctions_result.is_compliant:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=f"Sanctions check failed: {', '.join(sanctions_result.violations)}",
                    error_code="SANCTIONS_ERROR"
                )

            # Check Travel Rule
            travel_rule_ok = await self.compliance_service.check_travel_rule(payment)
            if not travel_rule_ok:
                 return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.COMPLIANCE_REVIEW, # Flag for missing info
                    message="Travel Rule Information Missing - Flagged for Review",
                    error_code="TRAVEL_RULE_REVIEW"
                )
            
            self.logger.info("Compliance validation passed", payment_id=payment.payment_id)
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Compliance validation passed"
            )
            
        except Exception as e:
            self.logger.error("Compliance validation failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Compliance validation failed: {str(e)}",
                error_code="COMPLIANCE_ERROR"
            )
    
    async def _check_liquidity(self, payment: CrossBorderPayment) -> PaymentResult:
        """Check liquidity availability using Smart Sweep Yield Service"""
        try:
            # Determine logic currency (e.g. USDC for settlement)
            currency = "USDC" # Defaulting for demo
            
            # Request Liquidity (Handles JIT Unwinding internally)
            liquidity_available = await self.yield_service.request_liquidity(
                payment.amount,
                currency
            )
            
            if not liquidity_available:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message="Insufficient liquidity (Hot + Yield) for payment",
                    error_code="INSUFFICIENT_LIQUIDITY"
                )
            
            self.logger.info("Liquidity check passed (Smart Sweep confirmed)", payment_id=payment.payment_id)
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Liquidity available"
            )
            
        except Exception as e:
            self.logger.error("Liquidity check failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Liquidity check failed: {str(e)}",
                error_code="LIQUIDITY_ERROR"
            )
    
    async def _lock_exchange_rate(self, payment: CrossBorderPayment) -> PaymentResult:
        """Lock exchange rate for payment"""
        try:
            # Get current exchange rate
            rate = await self.exchange_rate_service.get_exchange_rate(
                payment.from_currency, payment.to_currency
            )
            
            if not rate:
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message="Exchange rate not available",
                    error_code="EXCHANGE_RATE_ERROR"
                )
            
            # Lock the rate — duration comes from the agent credential if present, else settings default
            rate_lock_minutes = getattr(getattr(payment, "agent_credential", None), "rate_lock_duration_minutes", None)
            if rate_lock_minutes is None:
                rate_lock_minutes = self.settings.RATE_LOCK_DURATION_MINUTES
            rate_lock_ttl = rate_lock_minutes * 60
            rate_lock_key = f"rate_lock:{payment.payment_id}"
            await self.cache.set(rate_lock_key, float(rate), rate_lock_ttl)
            
            # Update payment with locked rate
            payment.exchange_rate = rate
            payment.converted_amount = payment.amount * rate
            
            self.logger.info("Exchange rate locked", payment_id=payment.payment_id, rate=rate)
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Exchange rate locked",
                exchange_rate_used=rate
            )
            
        except Exception as e:
            self.logger.error("Exchange rate locking failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Exchange rate locking failed: {str(e)}",
                error_code="EXCHANGE_RATE_ERROR"
            )
    
    async def _execute_mmo_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """Execute payment through MMO or HIFI Africa Rail"""
        try:
            # Check if this payment should be routed through HIFI
            use_hifi = self._should_use_hifi(payment)

            if use_hifi and self.hifi_adapter:
                return await self._execute_hifi_payment(payment)

            # Check MMO availability
            if payment.selected_route and payment.selected_route.to_mmo:
                mmo_available = await self.mmo_availability_service.is_available(payment.selected_route.to_mmo)

                if not mmo_available:
                    return PaymentResult(
                        success=False,
                        payment_id=payment.payment_id,
                        status=PaymentStatus.FAILED,
                        message="MMO provider not available",
                        error_code="MMO_UNAVAILABLE"
                    )

            # Mock MMO execution - in real implementation, this would call actual MMO APIs
            # Simulate processing delay
            await asyncio.sleep(0.5)

            # Generate mock MMO transaction ID
            mmo_tx_id = f"mmo_{payment.payment_id}_{datetime.now().timestamp()}"

            self.logger.info("MMO payment executed", payment_id=payment.payment_id, mmo_tx_id=mmo_tx_id)

            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.SETTLING,
                message="MMO payment executed successfully",
                transaction_hash=mmo_tx_id
            )

        except Exception as e:
            self.logger.error("MMO payment execution failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"MMO payment execution failed: {str(e)}",
                error_code="MMO_EXECUTION_ERROR"
            )

    def _should_use_hifi(self, payment: CrossBorderPayment) -> bool:
        """Determine if a payment should be routed through HIFI Africa Rail."""
        if not self.hifi_adapter or not self.settings.HIFI_ENABLED:
            return False

        # Circuit breaker check — skip HIFI if circuit is open
        if hasattr(self, "hifi_circuit_breaker") and self.hifi_circuit_breaker.is_open():
            self.logger.warning("HIFI circuit breaker is open, skipping")
            return False

        # Explicit rail_provider on the route takes priority
        if payment.selected_route and payment.selected_route.rail_provider == RailProvider.HIFI_AFRICA:
            return True

        # Explicit rail_provider on the payment takes priority
        if payment.rail_provider == RailProvider.HIFI_AFRICA:
            return True

        # Check if the destination country is in the HIFI allowed list
        recipient_country = payment.recipient.country.value
        if self.settings.HIFI_ALLOWED_COUNTRIES and recipient_country not in self.settings.HIFI_ALLOWED_COUNTRIES:
            return False

        # Check if HIFI supports this corridor
        return self.hifi_adapter.supports_direction(
            recipient_country,
            payment.direction.value if payment.direction else "payout",
        )

    async def _execute_hifi_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """Execute a payment through HIFI Africa Rail with fallback."""
        try:
            from packages.integrations.hifi.models import map_sender_to_hifi_kyc

            # Validate KYC completeness
            recipient_country = payment.recipient.country.value
            is_valid, missing = self.compliance_service.validate_hifi_kyc_completeness(
                payment.sender, recipient_country
            )
            if not is_valid:
                self.logger.warning(
                    "HIFI KYC incomplete, pausing for review",
                    payment_id=payment.payment_id,
                    missing_fields=missing,
                )
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.COMPLIANCE_REVIEW,
                    message=f"HIFI KYC data incomplete. Missing: {', '.join(missing)}",
                    error_code="HIFI_KYC_INCOMPLETE",
                    error_details={"missing_fields": missing},
                )

            # Map KYC data
            sender_kyc = map_sender_to_hifi_kyc(
                name=payment.sender.name,
                phone_number=payment.sender.phone_number,
                country_code=recipient_country,
                email=payment.sender.email,
                first_name=payment.sender.first_name,
                last_name=payment.sender.last_name,
                date_of_birth=payment.sender.date_of_birth,
                id_type=payment.sender.id_type,
                id_number=payment.sender.id_number,
                address_line1=payment.sender.address_line1,
                address_line2=payment.sender.address_line2,
                city=payment.sender.city,
                state_province_region=payment.sender.state_province_region,
                postal_code=payment.sender.postal_code,
                additional_id_type=payment.sender.additional_id_type,
                additional_id_number=payment.sender.additional_id_number,
            )

            # Determine payment method
            payment_method = "mobile_money"
            if payment.payment_method == PaymentMethod.BANK_TRANSFER:
                payment_method = "bank_transfer"

            # Execute via HIFI
            direction = payment.direction.value if payment.direction else "payout"
            tx_id = await self.hifi_adapter.execute_directed_transfer(
                direction=direction,
                amount=payment.amount,
                currency=payment.to_currency.value,
                payment_method=payment_method,
                country_code=recipient_country,
                sender_kyc=sender_kyc,
                reference=payment.reference_id,
            )

            # Update payment with HIFI tracking info
            payment.rail_provider = RailProvider.HIFI_AFRICA
            payment.provider_transaction_id = tx_id

            # Record success in circuit breaker
            if hasattr(self, "hifi_circuit_breaker"):
                self.hifi_circuit_breaker.record_success()

            self.logger.info(
                "HIFI payment executed",
                payment_id=payment.payment_id,
                hifi_tx_id=tx_id,
            )

            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.SETTLING,
                message="HIFI Africa Rail payment executed",
                transaction_hash=tx_id,
            )

        except Exception as e:
            # Record failure in circuit breaker
            if hasattr(self, "hifi_circuit_breaker"):
                self.hifi_circuit_breaker.record_failure()

            self.logger.error(
                "HIFI payment failed",
                payment_id=payment.payment_id,
                error=str(e),
            )

            # Fallback to existing MMO/bank providers if enabled
            if self.settings.HIFI_FALLBACK_ENABLED:
                self.logger.info(
                    "Falling back to existing provider",
                    payment_id=payment.payment_id,
                )
                # Clear HIFI rail selection and retry via standard MMO path
                payment.rail_provider = None
                await asyncio.sleep(0.5)
                mmo_tx_id = f"mmo_fallback_{payment.payment_id}_{datetime.now().timestamp()}"
                return PaymentResult(
                    success=True,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.SETTLING,
                    message="Payment executed via fallback provider (HIFI unavailable)",
                    transaction_hash=mmo_tx_id,
                )

            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"HIFI payment failed: {str(e)}",
                error_code="HIFI_EXECUTION_ERROR",
            )
    
    async def _settle_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """Settle payment on blockchain"""
        try:
            # Mock blockchain settlement - in real implementation, this would submit to Aptos
            # Simulate blockchain processing delay
            await asyncio.sleep(1.0)
            
            # Generate mock blockchain transaction hash
            blockchain_tx_hash = f"0x{str(payment.payment_id).replace('-', '')[:64]}"
            
            # Update payment with blockchain transaction
            payment.blockchain_tx_hash = blockchain_tx_hash
            
            self.logger.info("Payment settled on blockchain", payment_id=payment.payment_id, tx_hash=blockchain_tx_hash)
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.COMPLETED,
                message="Payment settled on blockchain",
                transaction_hash=blockchain_tx_hash
            )
            
        except Exception as e:
            self.logger.error("Blockchain settlement failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Blockchain settlement failed: {str(e)}",
                error_code="SETTLEMENT_ERROR"
            )
    
    async def _confirm_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """Confirm payment completion"""
        try:
            # Update payment status to completed
            payment.update_status(PaymentStatus.COMPLETED)
            
            # Send confirmation notifications (mock)
            await self._send_confirmation_notifications(payment)
            
            self.logger.info("Payment confirmed", payment_id=payment.payment_id)
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.COMPLETED,
                message="Payment confirmed successfully"
            )
            
        except Exception as e:
            self.logger.error("Payment confirmation failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Payment confirmation failed: {str(e)}",
                error_code="CONFIRMATION_ERROR"
            )
    
    async def _send_confirmation_notifications(self, payment: CrossBorderPayment):
        """Send confirmation notifications to sender and recipient"""
        try:
            # Mock SMS notifications
            sender_message = f"Your payment of {payment.amount} {payment.from_currency} to {payment.recipient.name} has been completed. Transaction ID: {payment.payment_id}"
            recipient_message = f"You have received {payment.converted_amount} {payment.to_currency} from {payment.sender.name}. Transaction ID: {payment.payment_id}"
            
            # In real implementation, this would integrate with SMS/email services
            self.logger.info("Confirmation notifications sent", 
                           payment_id=payment.payment_id,
                           sender_message=sender_message[:50] + "...",
                           recipient_message=recipient_message[:50] + "...")
            
        except Exception as e:
            self.logger.error("Failed to send confirmation notifications", error=str(e))
    
    async def _handle_payment_failure(self, payment: CrossBorderPayment, error_message: str) -> PaymentResult:
        """Handle payment failures with retry logic and fallback routes"""
        try:
            # Update payment status
            payment.update_status(PaymentStatus.FAILED)
            
            # Record failure metrics
            await self._record_payment_metrics(payment, 0, False)
            
            # In real implementation, this would implement retry logic and fallback routes
            self.logger.warning("Payment failed", payment_id=payment.payment_id, error=error_message)
            
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=error_message,
                error_code="PAYMENT_FAILED"
            )
            
        except Exception as e:
            self.logger.error("Failed to handle payment failure", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Payment failed: {error_message}",
                error_code="PAYMENT_FAILED"
            )
    
    async def _record_payment_metrics(self, payment: CrossBorderPayment, processing_time: float, success: bool):
        """Record payment processing metrics"""
        try:
            corridor = f"{payment.sender.country}-{payment.recipient.country}"
            
            await self.metrics_collector.record_payment_metrics(
                payment_id=str(payment.payment_id),
                amount=payment.amount,
                processing_time=processing_time,
                success=success,
                corridor=corridor
            )
            
        except Exception as e:
            self.logger.error("Failed to record payment metrics", error=str(e))
    
    async def track_payment_status(self, payment_id: str) -> PaymentStatus:
        """Real-time payment tracking"""
        try:
            # In real implementation, this would query the database
            # For now, return a mock status
            return PaymentStatus.COMPLETED
            
        except Exception as e:
            self.logger.error("Failed to track payment status", error=str(e))
            return PaymentStatus.FAILED
    
    async def get_payment_analytics(self) -> Dict[str, Any]:
        """Get payment processing analytics"""
        try:
            # Get metrics from metrics collector
            payment_metrics = await self.metrics_collector.get_payment_metrics()
            business_metrics = await self.metrics_collector.get_business_metrics()
            
            return {
                "payment_metrics": payment_metrics,
                "business_metrics": business_metrics,
                "cost_savings": {
                    "traditional_cost_percentage": 8.9,
                    "capp_cost_percentage": 0.8,
                    "savings_percentage": 8.1
                },
                "performance": {
                    "average_settlement_time_minutes": 5,
                    "traditional_settlement_time_days": 3,
                    "speed_improvement": 864  # 3 days vs 5 minutes
                }
            }
            
        except Exception as e:
            self.logger.error("Failed to get payment analytics", error=str(e))
            return {} 