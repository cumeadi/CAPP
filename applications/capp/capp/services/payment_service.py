"""
Payment Service for CAPP

Orchestrates the full payment processing pipeline using all five autonomous agents:
  1. Route Optimization  — finds the optimal corridor and MMO route
  2. Exchange Rate       — aggregates rates and locks the best rate
  3. Compliance          — KYC/AML/sanctions screening (runs in parallel with #4)
  4. Liquidity           — reserves funds in the target corridor pool
  5. Settlement          — submits the blockchain transaction on Aptos

The Saga pattern is used to guarantee clean rollback of any partial state when a
step fails mid-pipeline.  The AgentEventBus publishes lifecycle events that other
components (e.g. notification services, monitoring) can subscribe to without
coupling to this service.
"""

import asyncio
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentBatch,
    Currency,
)
from ..agents.base import agent_registry
from ..agents.event_bus import agent_event_bus, AgentEvent, AgentEventType
from ..agents.payment_saga import PaymentSaga
from ..agents.routing.route_optimization_agent import RouteOptimizationAgent, RouteOptimizationConfig
from ..agents.compliance.compliance_agent import ComplianceAgent, ComplianceConfig
from ..agents.liquidity.liquidity_agent import LiquidityAgent, LiquidityConfig
from ..agents.exchange.exchange_rate_agent import ExchangeRateAgent, ExchangeRateConfig
from ..agents.settlement.settlement_agent import SettlementAgent, SettlementConfig
from ..core.database import get_database_session
from ..core.redis import get_cache
from ..config.settings import get_settings
from ..repositories.payment import PaymentRepository
from ..utils.payment_mapper import crossborder_payment_to_db, db_payment_to_crossborder

logger = structlog.get_logger(__name__)


class PaymentService:
    """
    Orchestrates the complete payment processing workflow.

    All five agents are initialised once at startup and reused for every
    payment.  The Saga pattern ensures that reserved liquidity, locked
    exchange rates, and any other side-effects are reversed automatically
    if any step fails.
    """

    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
        self._initialize_agents()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialize_agents(self):
        """Create and register all five payment-processing agents."""
        try:
            self.route_agent = RouteOptimizationAgent(RouteOptimizationConfig())
            self.exchange_agent = ExchangeRateAgent(ExchangeRateConfig())
            self.compliance_agent = ComplianceAgent(ComplianceConfig())
            self.liquidity_agent = LiquidityAgent(LiquidityConfig())
            self.settlement_agent = SettlementAgent(SettlementConfig())

            # Register in the shared registry so health-checks can reach them
            agent_registry.register_agent_type("route_optimization", RouteOptimizationAgent)
            agent_registry.register_agent_type("exchange_rate", ExchangeRateAgent)
            agent_registry.register_agent_type("compliance", ComplianceAgent)
            agent_registry.register_agent_type("liquidity_management", LiquidityAgent)
            agent_registry.register_agent_type("settlement", SettlementAgent)

            self.logger.info("All payment agents initialised successfully")

        except Exception as e:
            self.logger.error("Failed to initialise agents", error=str(e))
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Run the full payment pipeline with automatic rollback on failure.

        Pipeline (with parallelism where safe):
            Step 1  – Route optimisation
            Step 2  – Exchange rate lock
            Step 3a – Compliance check     ┐  parallel
            Step 3b – Liquidity reservation┘
            Step 4  – Settlement
        """
        saga = PaymentSaga(payment.payment_id)

        self.logger.info(
            "Starting payment processing",
            payment_id=str(payment.payment_id),
            amount=str(payment.amount),
            from_country=payment.sender.country,
            to_country=payment.recipient.country,
        )

        try:
            # ── Step 1: Route optimisation ──────────────────────────────
            route_result = await self.route_agent.process_payment_with_retry(payment)
            if not route_result.success:
                return self._fail(payment, route_result.message, "ROUTE_OPTIMIZATION_ERROR")

            await agent_event_bus.publish(AgentEvent(
                event_type=AgentEventType.ROUTE_SELECTED,
                payment_id=payment.payment_id,
                agent_type="route_optimization",
                data={"route": str(payment.selected_route)},
            ))

            # ── Step 2: Lock exchange rate ──────────────────────────────
            rate_result = await self.exchange_agent.get_optimal_rate(
                payment.from_currency, payment.to_currency
            )
            if not rate_result.success or rate_result.rate is None:
                return self._fail(payment, rate_result.message, "EXCHANGE_RATE_ERROR")

            lock_result = await self.exchange_agent.lock_exchange_rate(payment, rate_result.rate)
            if not lock_result.success or lock_result.rate_lock_id is None:
                return self._fail(payment, lock_result.message, "EXCHANGE_RATE_LOCK_ERROR")

            # Attach the locked rate to the payment
            payment.exchange_rate = lock_result.rate

            # Register compensation: unlock rate if something later fails
            rate_lock_id = lock_result.rate_lock_id
            saga.register_compensation(
                "unlock_exchange_rate",
                lambda: self.exchange_agent.unlock_exchange_rate(rate_lock_id),
            )

            await agent_event_bus.publish(AgentEvent(
                event_type=AgentEventType.RATE_LOCKED,
                payment_id=payment.payment_id,
                agent_type="exchange_rate",
                data={"rate": str(lock_result.rate), "lock_id": rate_lock_id},
            ))

            # ── Step 3: Compliance + Liquidity in parallel ──────────────
            compliance_task = asyncio.create_task(
                self.compliance_agent.validate_payment_compliance(payment)
            )
            liquidity_task = asyncio.create_task(
                self.liquidity_agent.reserve_liquidity(payment)
            )

            compliance_result, liquidity_result = await asyncio.gather(
                compliance_task, liquidity_task, return_exceptions=True
            )

            # Handle compliance result
            if isinstance(compliance_result, Exception):
                await saga.rollback()
                return self._fail(payment, str(compliance_result), "COMPLIANCE_ERROR")
            if not compliance_result.is_compliant:
                await saga.rollback()
                await agent_event_bus.publish(AgentEvent(
                    event_type=AgentEventType.COMPLIANCE_FAILED,
                    payment_id=payment.payment_id,
                    agent_type="compliance",
                    data={"violations": compliance_result.violations},
                ))
                return self._fail(
                    payment,
                    f"Compliance failed: {', '.join(compliance_result.violations)}",
                    "COMPLIANCE_REJECTED",
                )

            await agent_event_bus.publish(AgentEvent(
                event_type=AgentEventType.COMPLIANCE_PASSED,
                payment_id=payment.payment_id,
                agent_type="compliance",
                data={"risk_level": compliance_result.risk_level},
            ))

            # Handle liquidity result
            if isinstance(liquidity_result, Exception):
                await saga.rollback()
                return self._fail(payment, str(liquidity_result), "LIQUIDITY_ERROR")
            if not liquidity_result.success or liquidity_result.reservation_id is None:
                await saga.rollback()
                await agent_event_bus.publish(AgentEvent(
                    event_type=AgentEventType.LIQUIDITY_INSUFFICIENT,
                    payment_id=payment.payment_id,
                    agent_type="liquidity_management",
                    data={"available": str(liquidity_result.available_amount)},
                ))
                return self._fail(payment, liquidity_result.message, "INSUFFICIENT_LIQUIDITY")

            # Register compensation: release reservation if settlement fails
            reservation_id = liquidity_result.reservation_id
            saga.register_compensation(
                "release_liquidity",
                lambda: self.liquidity_agent.release_liquidity(reservation_id),
            )

            await agent_event_bus.publish(AgentEvent(
                event_type=AgentEventType.LIQUIDITY_RESERVED,
                payment_id=payment.payment_id,
                agent_type="liquidity_management",
                data={"reservation_id": reservation_id, "amount": str(liquidity_result.reserved_amount)},
            ))

            # ── Step 4: Settlement ───────────────────────────────────────
            settlement_result = await self.settlement_agent.process_payment(payment)
            if not settlement_result.success:
                await saga.rollback()
                await agent_event_bus.publish(AgentEvent(
                    event_type=AgentEventType.SETTLEMENT_FAILED,
                    payment_id=payment.payment_id,
                    agent_type="settlement",
                    data={"error": settlement_result.message},
                ))
                return self._fail(payment, settlement_result.message, "SETTLEMENT_ERROR")

            # ── Success ─────────────────────────────────────────────────
            payment.update_status(PaymentStatus.COMPLETED)
            payment.blockchain_tx_hash = settlement_result.transaction_hash
            await self._store_payment(payment)

            await agent_event_bus.publish(AgentEvent(
                event_type=AgentEventType.PAYMENT_COMPLETED,
                payment_id=payment.payment_id,
                agent_type="payment_service",
                data={"tx_hash": settlement_result.transaction_hash},
            ))

            self.logger.info(
                "Payment completed successfully",
                payment_id=str(payment.payment_id),
                tx_hash=settlement_result.transaction_hash,
                steps_completed=saga.completed_step_names,
            )

            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.COMPLETED,
                message="Payment processed successfully",
                transaction_hash=settlement_result.transaction_hash,
                estimated_delivery_time=(
                    payment.selected_route.estimated_delivery_time
                    if payment.selected_route else None
                ),
                fees_charged=payment.fees,
                exchange_rate_used=payment.exchange_rate,
            )

        except Exception as e:
            self.logger.error(
                "Unexpected error during payment processing",
                payment_id=str(payment.payment_id),
                error=str(e),
                exc_info=True,
            )
            await saga.rollback()
            payment.update_status(PaymentStatus.FAILED)

            await agent_event_bus.publish(AgentEvent(
                event_type=AgentEventType.PAYMENT_FAILED,
                payment_id=payment.payment_id,
                agent_type="payment_service",
                data={"error": str(e)},
            ))

            return self._fail(payment, f"Payment processing failed: {e}", "PROCESSING_ERROR")

    async def get_payment(self, payment_id: UUID) -> Optional[CrossBorderPayment]:
        """Retrieve a payment by ID from the database."""
        try:
            async with get_database_session() as session:
                repo = PaymentRepository(session)
                db_payment = await repo.get_by_id(payment_id)
                if not db_payment:
                    self.logger.warning("Payment not found", payment_id=str(payment_id))
                    return None
                return db_payment_to_crossborder(db_payment)
        except Exception as e:
            self.logger.error("Failed to get payment", payment_id=str(payment_id), error=str(e))
            return None

    async def cancel_payment(self, payment_id: UUID) -> PaymentResult:
        """Cancel a payment if it is still in a cancellable state."""
        try:
            payment = await self.get_payment(payment_id)
            if not payment:
                return PaymentResult(
                    success=False,
                    payment_id=payment_id,
                    status=PaymentStatus.FAILED,
                    message="Payment not found",
                    error_code="PAYMENT_NOT_FOUND",
                )

            if not payment.can_be_cancelled():
                return PaymentResult(
                    success=False,
                    payment_id=payment_id,
                    status=PaymentStatus.FAILED,
                    message="Payment cannot be cancelled in its current state",
                    error_code="CANCELLATION_NOT_ALLOWED",
                )

            payment.update_status(PaymentStatus.CANCELLED)
            await self._store_payment(payment)
            self.logger.info("Payment cancelled", payment_id=str(payment_id))

            return PaymentResult(
                success=True,
                payment_id=payment_id,
                status=PaymentStatus.CANCELLED,
                message="Payment cancelled successfully",
            )
        except Exception as e:
            self.logger.error("Failed to cancel payment", payment_id=str(payment_id), error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                message=f"Failed to cancel payment: {e}",
                error_code="CANCELLATION_ERROR",
            )

    async def process_batch_payments(self, payments: List[CrossBorderPayment]) -> List[PaymentResult]:
        """Process multiple payments concurrently."""
        self.logger.info("Processing batch payments", count=len(payments))
        tasks = [self.process_payment(p) for p in payments]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed: List[PaymentResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(PaymentResult(
                    success=False,
                    payment_id=payments[i].payment_id,
                    status=PaymentStatus.FAILED,
                    message=f"Batch processing failed: {result}",
                    error_code="BATCH_PROCESSING_ERROR",
                ))
            else:
                processed.append(result)

        self.logger.info(
            "Batch processing complete",
            total=len(payments),
            successful=sum(1 for r in processed if r.success),
            failed=sum(1 for r in processed if not r.success),
        )
        return processed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fail(
        self,
        payment: CrossBorderPayment,
        message: str,
        error_code: str,
    ) -> PaymentResult:
        """Build a failed PaymentResult and update payment status."""
        payment.update_status(PaymentStatus.FAILED)
        self.logger.warning(
            "Payment failed",
            payment_id=str(payment.payment_id),
            error_code=error_code,
            message=message,
        )
        return PaymentResult(
            success=False,
            payment_id=payment.payment_id,
            status=PaymentStatus.FAILED,
            message=message,
            error_code=error_code,
        )

    async def _store_payment(self, payment: CrossBorderPayment, user_id: Optional[UUID] = None) -> None:
        """Persist payment to the database (create or update)."""
        try:
            async with get_database_session() as session:
                repo = PaymentRepository(session)
                db_payment = crossborder_payment_to_db(payment, user_id=user_id)
                existing = await repo.get_by_id(payment.payment_id)

                if existing:
                    await repo.update_status(
                        payment.payment_id,
                        payment.status.value,
                        blockchain_tx_hash=payment.blockchain_tx_hash,
                    )
                    self.logger.info("Payment updated in database", payment_id=str(payment.payment_id))
                else:
                    await repo.create(
                        payment_id=db_payment.id,
                        user_id=db_payment.user_id,
                        reference=db_payment.reference,
                        sender_name=db_payment.sender_name,
                        sender_phone=db_payment.sender_phone,
                        sender_country=db_payment.sender_country,
                        recipient_name=db_payment.recipient_name,
                        recipient_phone=db_payment.recipient_phone,
                        recipient_country=db_payment.recipient_country,
                        payment_type=db_payment.payment_type,
                        payment_method=db_payment.payment_method,
                        amount=db_payment.amount,
                        from_currency=db_payment.from_currency,
                        to_currency=db_payment.to_currency,
                        exchange_rate=db_payment.exchange_rate,
                        converted_amount=db_payment.converted_amount,
                        fees=db_payment.fees,
                        total_cost=db_payment.total_cost,
                        status=db_payment.status,
                        sender_email=db_payment.sender_email,
                        sender_address=db_payment.sender_address,
                        recipient_email=db_payment.recipient_email,
                        recipient_address=db_payment.recipient_address,
                        recipient_bank_account=db_payment.recipient_bank_account,
                        recipient_bank_name=db_payment.recipient_bank_name,
                        recipient_mmo_account=db_payment.recipient_mmo_account,
                        recipient_mmo_provider=db_payment.recipient_mmo_provider,
                        route_id=db_payment.route_id,
                        blockchain_tx_hash=db_payment.blockchain_tx_hash,
                        agent_id=db_payment.agent_id,
                        workflow_id=db_payment.workflow_id,
                        compliance_status=db_payment.compliance_status,
                        fraud_score=db_payment.fraud_score,
                        risk_level=db_payment.risk_level,
                        sender_kyc_verified=db_payment.sender_kyc_verified,
                        recipient_kyc_verified=db_payment.recipient_kyc_verified,
                        description=db_payment.description,
                        metadata=db_payment.metadata,
                        offline_queued=db_payment.offline_queued,
                        created_at=db_payment.created_at,
                        expires_at=db_payment.expires_at,
                    )
                    self.logger.info("Payment stored in database", payment_id=str(payment.payment_id))
        except Exception as e:
            self.logger.error(
                "Failed to store payment",
                payment_id=str(payment.payment_id),
                error=str(e),
            )
            raise
