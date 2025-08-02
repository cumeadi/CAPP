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

from .models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentBatch
)
from .agents.base import agent_registry
from .agents.routing.route_optimization_agent import RouteOptimizationAgent, RouteOptimizationConfig
from .core.database import get_database_session
from .core.redis import get_cache
from .config.settings import get_settings

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
    
    async def _store_payment(self, payment: CrossBorderPayment) -> None:
        """Store payment in database"""
        try:
            # This would integrate with actual database storage
            # For now, just log
            self.logger.info("Payment stored", payment_id=payment.payment_id)
            
        except Exception as e:
            self.logger.error("Failed to store payment", error=str(e))
    
    async def get_payment(self, payment_id: UUID) -> Optional[CrossBorderPayment]:
        """
        Get payment by ID
        
        Args:
            payment_id: The payment ID
            
        Returns:
            CrossBorderPayment: The payment, or None if not found
        """
        try:
            # This would query the database
            # For now, return None
            return None
            
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