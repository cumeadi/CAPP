"""
Payment Service for CAPP

This service orchestrates the payment processing workflow using autonomous agents
for route optimization, compliance checking, and settlement.
"""

import asyncio
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from capp.models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentBatch
)
from capp.agents.base import agent_registry
from capp.agents.routing.route_optimization_agent import RouteOptimizationAgent, RouteOptimizationConfig
from capp.core.database import AsyncSessionLocal
from capp.core.redis import get_cache
from capp.config.settings import get_settings
from capp.repositories.payment import PaymentRepository
from capp.utils.payment_mapper import crossborder_payment_to_db, db_payment_to_crossborder

logger = structlog.get_logger(__name__)


class PaymentService:
    """
    Payment Service
    
    Orchestrates the complete payment processing workflow including:
    - Route optimization
    - Compliance checking
    - Settlement processing
    - Status tracking
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize payment processing agents"""
        try:
            # Register route optimization agent
            route_config = RouteOptimizationConfig()
            route_agent = RouteOptimizationAgent(route_config)
            agent_registry.register_agent_type("route_optimization", RouteOptimizationAgent)
            
            self.logger.info("Payment service agents initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize agents", error=str(e))
            raise
    
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process a cross-border payment through the complete workflow
        
        Args:
            payment: The payment to process
            
        Returns:
            PaymentResult: The result of the payment processing
        """
        try:
            self.logger.info(
                "Processing payment",
                payment_id=payment.payment_id,
                amount=payment.amount,
                from_country=payment.sender.country,
                to_country=payment.recipient.country
            )
            
            # Step 1: Route Optimization
            route_result = await self._optimize_route(payment)
            if not route_result.success:
                return route_result
            
            # Step 2: Compliance Check
            compliance_result = await self._check_compliance(payment)
            if not compliance_result.success:
                return compliance_result
            
            # Step 3: Fraud Detection
            fraud_result = await self._detect_fraud(payment)
            if not fraud_result.success:
                return fraud_result
            
            # Step 4: Settlement
            settlement_result = await self._settle_payment(payment)
            if not settlement_result.success:
                return settlement_result
            
            # Step 5: Update payment status
            payment.update_status(PaymentStatus.COMPLETED)
            
            # Step 6: Store payment in database
            await self._store_payment(payment)
            
            self.logger.info(
                "Payment processed successfully",
                payment_id=payment.payment_id,
                transaction_hash=settlement_result.transaction_hash
            )
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.COMPLETED,
                message="Payment processed successfully",
                transaction_hash=settlement_result.transaction_hash,
                estimated_delivery_time=payment.selected_route.estimated_delivery_time if payment.selected_route else None,
                fees_charged=payment.fees,
                exchange_rate_used=payment.exchange_rate
            )
            
        except Exception as e:
            self.logger.error(
                "Payment processing failed",
                payment_id=payment.payment_id,
                error=str(e),
                exc_info=True
            )
            
            payment.update_status(PaymentStatus.FAILED)
            
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Payment processing failed: {str(e)}",
                error_code="PROCESSING_ERROR"
            )
    
    async def _optimize_route(self, payment: CrossBorderPayment) -> PaymentResult:
        """Optimize payment route using route optimization agent"""
        try:
            # Get route optimization agent
            route_agents = agent_registry.get_agents_by_type("route_optimization")
            if not route_agents:
                # Create new agent if none exists
                route_config = RouteOptimizationConfig()
                route_agent = RouteOptimizationAgent(route_config)
                agent_registry.create_agent("route_optimization", route_config)
                route_agents = [route_agent]
            
            route_agent = route_agents[0]
            
            # Process payment with route optimization
            result = await route_agent.process_payment_with_retry(payment)
            
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
    
    async def _check_compliance(self, payment: CrossBorderPayment) -> PaymentResult:
        """Check compliance requirements for the payment"""
        try:
            # This would integrate with actual compliance service
            # For now, return success
            self.logger.info("Compliance check passed", payment_id=payment.payment_id)
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Compliance check passed"
            )
            
        except Exception as e:
            self.logger.error("Compliance check failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Compliance check failed: {str(e)}",
                error_code="COMPLIANCE_ERROR"
            )
    
    async def _detect_fraud(self, payment: CrossBorderPayment) -> PaymentResult:
        """Detect potential fraud in the payment"""
        try:
            # This would integrate with actual fraud detection service
            # For now, return success
            self.logger.info("Fraud detection passed", payment_id=payment.payment_id)
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Fraud detection passed"
            )
            
        except Exception as e:
            self.logger.error("Fraud detection failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Fraud detection failed: {str(e)}",
                error_code="FRAUD_DETECTION_ERROR"
            )
    
    async def _settle_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """Settle the payment on the blockchain"""
        try:
            # This would integrate with actual settlement service
            # For now, return mock success
            mock_tx_hash = f"0x{payment.payment_id.hex[:64]}"
            
            payment.blockchain_tx_hash = mock_tx_hash
            
            self.logger.info(
                "Payment settled",
                payment_id=payment.payment_id,
                transaction_hash=mock_tx_hash
            )
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.SETTLING,
                message="Payment settled successfully",
                transaction_hash=mock_tx_hash
            )
            
        except Exception as e:
            self.logger.error("Payment settlement failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Payment settlement failed: {str(e)}",
                error_code="SETTLEMENT_ERROR"
            )
    
    async def _store_payment(self, payment: CrossBorderPayment, user_id: Optional[UUID] = None) -> None:
        """Store payment in database"""
        try:
            async with AsyncSessionLocal() as session:
                repo = PaymentRepository(session)

                # Convert Pydantic model to SQLAlchemy model
                db_payment = crossborder_payment_to_db(payment, user_id=user_id)

                # Check if payment already exists (update scenario)
                existing_payment = await repo.get_by_id(payment.payment_id)

                if existing_payment:
                    # Update existing payment
                    await repo.update_status(
                        payment.payment_id,
                        payment.status.value,
                        blockchain_tx_hash=payment.blockchain_tx_hash
                    )
                    self.logger.info("Payment updated", payment_id=payment.payment_id)
                else:
                    # Create new payment
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
                    self.logger.info("Payment stored", payment_id=payment.payment_id)

        except Exception as e:
            self.logger.error("Failed to store payment", payment_id=payment.payment_id, error=str(e))
            raise
    
    async def get_payment(self, payment_id: UUID) -> Optional[CrossBorderPayment]:
        """
        Get payment by ID

        Args:
            payment_id: The payment ID

        Returns:
            CrossBorderPayment: The payment, or None if not found
        """
        try:
            async with AsyncSessionLocal() as session:
                repo = PaymentRepository(session)

                # Get payment from database
                db_payment = await repo.get_by_id(payment_id)

                if not db_payment:
                    self.logger.warning("Payment not found", payment_id=payment_id)
                    return None

                # Convert SQLAlchemy model to Pydantic model
                payment = db_payment_to_crossborder(db_payment)

                self.logger.info("Payment retrieved", payment_id=payment_id)
                return payment

        except Exception as e:
            self.logger.error("Failed to get payment", payment_id=payment_id, error=str(e))
            return None
    
    async def cancel_payment(self, payment_id: UUID) -> PaymentResult:
        """
        Cancel a payment
        
        Args:
            payment_id: The payment ID to cancel
            
        Returns:
            PaymentResult: The result of the cancellation
        """
        try:
            payment = await self.get_payment(payment_id)
            
            if not payment:
                return PaymentResult(
                    success=False,
                    payment_id=payment_id,
                    status=PaymentStatus.FAILED,
                    message="Payment not found",
                    error_code="PAYMENT_NOT_FOUND"
                )
            
            if not payment.can_be_cancelled():
                return PaymentResult(
                    success=False,
                    payment_id=payment_id,
                    status=PaymentStatus.FAILED,
                    message="Payment cannot be cancelled",
                    error_code="CANCELLATION_NOT_ALLOWED"
                )
            
            # Update payment status
            payment.update_status(PaymentStatus.CANCELLED)
            
            # Store updated payment
            await self._store_payment(payment)
            
            self.logger.info("Payment cancelled", payment_id=payment_id)
            
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                status=PaymentStatus.CANCELLED,
                message="Payment cancelled successfully"
            )
            
        except Exception as e:
            self.logger.error("Failed to cancel payment", payment_id=payment_id, error=str(e))
            
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                message=f"Failed to cancel payment: {str(e)}",
                error_code="CANCELLATION_ERROR"
            )
    
    async def process_batch_payments(self, payments: List[CrossBorderPayment]) -> List[PaymentResult]:
        """
        Process multiple payments in batch
        
        Args:
            payments: List of payments to process
            
        Returns:
            List[PaymentResult]: Results for each payment
        """
        try:
            self.logger.info("Processing batch payments", count=len(payments))
            
            # Process payments concurrently
            tasks = [self.process_payment(payment) for payment in payments]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to failed results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(PaymentResult(
                        success=False,
                        payment_id=payments[i].payment_id,
                        status=PaymentStatus.FAILED,
                        message=f"Batch processing failed: {str(result)}",
                        error_code="BATCH_PROCESSING_ERROR"
                    ))
                else:
                    processed_results.append(result)
            
            self.logger.info(
                "Batch processing completed",
                total=len(payments),
                successful=sum(1 for r in processed_results if r.success),
                failed=sum(1 for r in processed_results if not r.success)
            )
            
            return processed_results
            
        except Exception as e:
            self.logger.error("Batch processing failed", error=str(e))
            raise 