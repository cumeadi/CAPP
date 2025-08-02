"""
Payment Workflow Orchestrator

This module provides a specialized orchestrator for payment processing workflows,
extracting the payment-specific orchestration logic from CAPP into a reusable package.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from uuid import uuid4
import structlog

from pydantic import BaseModel, Field

from packages.core.orchestration.orchestrator import (
    FinancialOrchestrator, OrchestrationConfig, OrchestrationWorkflow, 
    OrchestrationStep, OrchestrationResult
)
from packages.core.agents.base import BaseFinancialAgent, AgentRegistry, ProcessingResult
from packages.core.agents.financial_base import FinancialTransaction, FinancialProcessingResult
from packages.core.performance.tracker import PerformanceTracker


logger = structlog.get_logger(__name__)


class PaymentWorkflowStep(str):
    """Payment workflow step identifiers"""
    CREATE_PAYMENT = "create_payment"
    VALIDATE_PAYMENT = "validate_payment"
    OPTIMIZE_ROUTE = "optimize_route"
    VALIDATE_COMPLIANCE = "validate_compliance"
    CHECK_LIQUIDITY = "check_liquidity"
    LOCK_EXCHANGE_RATE = "lock_exchange_rate"
    EXECUTE_MMO = "execute_mmo"
    SETTLE_PAYMENT = "settle_payment"
    CONFIRM_PAYMENT = "confirm_payment"


class PaymentWorkflowConfig(BaseModel):
    """Configuration for payment workflow orchestration"""
    # Workflow settings
    enable_parallel_processing: bool = False
    enable_consensus: bool = True
    enable_circuit_breaker: bool = True
    
    # Step timeouts (in seconds)
    create_payment_timeout: float = 10.0
    validate_payment_timeout: float = 5.0
    optimize_route_timeout: float = 15.0
    validate_compliance_timeout: float = 20.0
    check_liquidity_timeout: float = 10.0
    lock_exchange_rate_timeout: float = 10.0
    execute_mmo_timeout: float = 30.0
    settle_payment_timeout: float = 60.0
    confirm_payment_timeout: float = 10.0
    
    # Retry settings
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Performance settings
    enable_performance_tracking: bool = True
    performance_sampling_rate: float = 1.0


class PaymentWorkflowResult(BaseModel):
    """Result of payment workflow processing"""
    success: bool
    payment_id: str
    workflow_id: str
    status: str
    message: str
    processing_time: float
    step_results: Dict[str, ProcessingResult]
    final_result: Optional[ProcessingResult] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Payment-specific fields
    transaction_hash: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    fees_charged: Optional[Decimal] = None
    exchange_rate_used: Optional[Decimal] = None


class PaymentWorkflowOrchestrator:
    """
    Specialized orchestrator for payment processing workflows
    
    This class extracts the payment-specific orchestration logic from CAPP
    and provides a reusable interface for payment processing across different
    applications.
    """
    
    def __init__(
        self, 
        agent_registry: AgentRegistry,
        config: PaymentWorkflowConfig = None
    ):
        self.agent_registry = agent_registry
        self.config = config or PaymentWorkflowConfig()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize the core orchestrator
        orchestration_config = OrchestrationConfig(
            max_concurrent_transactions=100,
            transaction_timeout=300.0,
            retry_attempts=self.config.max_retry_attempts,
            retry_delay=self.config.retry_delay,
            consensus_threshold=0.7,
            consensus_timeout=30.0,
            enable_performance_tracking=self.config.enable_performance_tracking,
            performance_sampling_rate=self.config.performance_sampling_rate,
            enable_metrics=True,
            enable_logging=True,
            circuit_breaker_enabled=self.config.enable_circuit_breaker,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=60.0
        )
        
        self.orchestrator = FinancialOrchestrator(orchestration_config)
        self.performance_tracker = PerformanceTracker()
        
        # Register payment workflow
        self._register_payment_workflow()
        
        self.logger.info("Payment workflow orchestrator initialized")
    
    def _register_payment_workflow(self) -> None:
        """Register the payment processing workflow"""
        workflow = OrchestrationWorkflow(
            workflow_id="payment_processing",
            workflow_name="Cross-Border Payment Processing",
            steps=[
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.CREATE_PAYMENT,
                    step_name="Create Payment",
                    agent_type="payment_service",
                    required=True,
                    timeout=self.config.create_payment_timeout,
                    retry_attempts=self.config.max_retry_attempts
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.VALIDATE_PAYMENT,
                    step_name="Validate Payment",
                    agent_type="payment_service",
                    required=True,
                    timeout=self.config.validate_payment_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.CREATE_PAYMENT]
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.OPTIMIZE_ROUTE,
                    step_name="Optimize Route",
                    agent_type="route_optimization",
                    required=True,
                    timeout=self.config.optimize_route_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.VALIDATE_PAYMENT]
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.VALIDATE_COMPLIANCE,
                    step_name="Validate Compliance",
                    agent_type="compliance",
                    required=True,
                    timeout=self.config.validate_compliance_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.OPTIMIZE_ROUTE]
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.CHECK_LIQUIDITY,
                    step_name="Check Liquidity",
                    agent_type="liquidity",
                    required=True,
                    timeout=self.config.check_liquidity_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.VALIDATE_COMPLIANCE]
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.LOCK_EXCHANGE_RATE,
                    step_name="Lock Exchange Rate",
                    agent_type="exchange_rate",
                    required=True,
                    timeout=self.config.lock_exchange_rate_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.CHECK_LIQUIDITY]
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.EXECUTE_MMO,
                    step_name="Execute MMO Payment",
                    agent_type="mmo_service",
                    required=True,
                    timeout=self.config.execute_mmo_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.LOCK_EXCHANGE_RATE]
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.SETTLE_PAYMENT,
                    step_name="Settle Payment",
                    agent_type="settlement",
                    required=True,
                    timeout=self.config.settle_payment_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.EXECUTE_MMO]
                ),
                OrchestrationStep(
                    step_id=PaymentWorkflowStep.CONFIRM_PAYMENT,
                    step_name="Confirm Payment",
                    agent_type="payment_service",
                    required=True,
                    timeout=self.config.confirm_payment_timeout,
                    retry_attempts=self.config.max_retry_attempts,
                    dependencies=[PaymentWorkflowStep.SETTLE_PAYMENT]
                )
            ],
            max_parallel_steps=1 if not self.config.enable_parallel_processing else 3,
            timeout=300.0
        )
        
        self.orchestrator.register_workflow(workflow)
        self.logger.info("Payment workflow registered")
    
    async def process_payment(
        self, 
        payment_request: Dict[str, Any]
    ) -> PaymentWorkflowResult:
        """
        Process a payment through the complete workflow
        
        Args:
            payment_request: Payment request data
            
        Returns:
            PaymentWorkflowResult: Complete payment processing result
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                "Starting payment workflow processing",
                request_id=payment_request.get("reference_id"),
                amount=payment_request.get("amount"),
                from_country=payment_request.get("sender_country"),
                to_country=payment_request.get("recipient_country")
            )
            
            # Create financial transaction from payment request
            transaction = self._create_financial_transaction(payment_request)
            
            # Process through orchestration engine
            orchestration_result = await self.orchestrator.process_transaction(
                transaction, 
                "payment_processing"
            )
            
            # Convert to payment-specific result
            payment_result = self._convert_to_payment_result(
                orchestration_result, 
                payment_request.get("reference_id", str(uuid4())),
                start_time
            )
            
            # Record performance metrics
            if self.config.enable_performance_tracking:
                await self._record_payment_metrics(payment_result, start_time)
            
            self.logger.info(
                "Payment workflow processing completed",
                payment_id=payment_result.payment_id,
                success=payment_result.success,
                processing_time=payment_result.processing_time
            )
            
            return payment_result
            
        except Exception as e:
            self.logger.error(
                "Payment workflow processing failed",
                request_id=payment_request.get("reference_id"),
                error=str(e),
                exc_info=True
            )
            
            return PaymentWorkflowResult(
                success=False,
                payment_id=payment_request.get("reference_id", str(uuid4())),
                workflow_id="payment_processing",
                status="failed",
                message=f"Payment workflow processing failed: {str(e)}",
                processing_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
                step_results={},
                error_code="WORKFLOW_ERROR"
            )
    
    def _create_financial_transaction(self, payment_request: Dict[str, Any]) -> FinancialTransaction:
        """Create a financial transaction from payment request"""
        return FinancialTransaction(
            transaction_id=payment_request.get("reference_id", str(uuid4())),
            transaction_type="cross_border_payment",
            amount=Decimal(str(payment_request.get("amount", 0))),
            currency=payment_request.get("from_currency", "USD"),
            metadata={
                "payment_request": payment_request,
                "payment_type": payment_request.get("payment_type", "personal_remittance"),
                "payment_method": payment_request.get("payment_method", "mobile_money"),
                "sender_country": payment_request.get("sender_country"),
                "recipient_country": payment_request.get("recipient_country"),
                "to_currency": payment_request.get("to_currency"),
                "sender_name": payment_request.get("sender_name"),
                "sender_phone": payment_request.get("sender_phone"),
                "recipient_name": payment_request.get("recipient_name"),
                "recipient_phone": payment_request.get("recipient_phone")
            }
        )
    
    def _convert_to_payment_result(
        self, 
        orchestration_result: OrchestrationResult,
        payment_id: str,
        start_time: datetime
    ) -> PaymentWorkflowResult:
        """Convert orchestration result to payment-specific result"""
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Extract payment-specific data from step results
        transaction_hash = None
        estimated_delivery_time = None
        fees_charged = None
        exchange_rate_used = None
        
        if orchestration_result.success and orchestration_result.final_result:
            final_metadata = orchestration_result.final_result.metadata or {}
            transaction_hash = final_metadata.get("transaction_hash")
            estimated_delivery_time = final_metadata.get("estimated_delivery_time")
            fees_charged = final_metadata.get("fees_charged")
            exchange_rate_used = final_metadata.get("exchange_rate_used")
        
        return PaymentWorkflowResult(
            success=orchestration_result.success,
            payment_id=payment_id,
            workflow_id=orchestration_result.workflow_id,
            status=orchestration_result.status,
            message=orchestration_result.message,
            processing_time=processing_time,
            step_results=orchestration_result.step_results,
            final_result=orchestration_result.final_result,
            error_code=orchestration_result.error_code,
            metadata=orchestration_result.metadata,
            transaction_hash=transaction_hash,
            estimated_delivery_time=estimated_delivery_time,
            fees_charged=fees_charged,
            exchange_rate_used=exchange_rate_used
        )
    
    async def _record_payment_metrics(
        self, 
        payment_result: PaymentWorkflowResult,
        start_time: datetime
    ) -> None:
        """Record payment processing metrics"""
        try:
            await self.performance_tracker.record_transaction_metrics(
                transaction_id=payment_result.payment_id,
                transaction_type="cross_border_payment",
                processing_time=payment_result.processing_time,
                success=payment_result.success,
                metadata={
                    "workflow_id": payment_result.workflow_id,
                    "status": payment_result.status,
                    "error_code": payment_result.error_code
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to record payment metrics: {str(e)}")
    
    async def get_payment_workflow_metrics(self) -> Dict[str, Any]:
        """Get payment workflow performance metrics"""
        try:
            orchestration_metrics = await self.orchestrator.get_orchestration_metrics()
            performance_metrics = await self.performance_tracker.get_metrics()
            
            return {
                "orchestration": orchestration_metrics,
                "performance": performance_metrics,
                "workflow_type": "payment_processing"
            }
        except Exception as e:
            self.logger.error(f"Failed to get payment workflow metrics: {str(e)}")
            return {}
    
    async def get_workflow_status(self, payment_id: str) -> Optional[str]:
        """Get the status of a specific payment workflow"""
        try:
            # This would typically query a persistent store
            # For now, return None as this would need integration with the actual storage
            return None
        except Exception as e:
            self.logger.error(f"Failed to get workflow status for {payment_id}: {str(e)}")
            return None 