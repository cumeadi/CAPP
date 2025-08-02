"""
Refactored Payment Orchestration Service for CAPP

This service now uses the extracted orchestration packages from the canza-platform
instead of the original monolithic implementation.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import structlog

from .models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    PaymentType, PaymentMethod, Country, Currency, MMOProvider
)
from .agents.base import agent_registry
from .services.payment_service import PaymentService
from .services.exchange_rates import ExchangeRateService
from .services.compliance import ComplianceService
from .services.mmo_availability import MMOAvailabilityService
from .services.metrics import MetricsCollector
from .core.redis import get_cache
from .config.settings import get_settings

# Import from extracted orchestration packages
from packages.core.orchestration import (
    PaymentWorkflowOrchestrator,
    PaymentWorkflowConfig,
    PaymentWorkflowResult,
    PaymentWorkflowFactory,
    WorkflowType
)
from packages.core.agents.base import AgentRegistry

logger = structlog.get_logger(__name__)


class RefactoredPaymentOrchestrationService:
    """
    Refactored Payment Orchestration Service
    
    This service now leverages the extracted orchestration packages to provide
    the same functionality as the original service but with better separation
    of concerns and reusability.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
        
        # Core services (kept for backward compatibility)
        self.payment_service = PaymentService()
        self.exchange_rate_service = ExchangeRateService()
        self.compliance_service = ComplianceService()
        self.mmo_availability_service = MMOAvailabilityService()
        self.metrics_collector = MetricsCollector()
        
        # Initialize orchestration components
        self._initialize_orchestration()
    
    def _initialize_orchestration(self):
        """Initialize orchestration components"""
        try:
            # Create agent registry adapter
            self.agent_registry = self._create_agent_registry_adapter()
            
            # Create workflow factory
            self.workflow_factory = PaymentWorkflowFactory(self.agent_registry)
            
            # Create default workflow orchestrator
            self.default_orchestrator = self.workflow_factory.create_workflow(
                WorkflowType.STANDARD
            )
            
            # Create specialized orchestrators for different use cases
            self.fast_track_orchestrator = self.workflow_factory.create_workflow(
                WorkflowType.FAST_TRACK
            )
            
            self.high_value_orchestrator = self.workflow_factory.create_workflow(
                WorkflowType.HIGH_VALUE
            )
            
            self.compliance_heavy_orchestrator = self.workflow_factory.create_workflow(
                WorkflowType.COMPLIANCE_HEAVY
            )
            
            self.logger.info("Refactored payment orchestration initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize orchestration", error=str(e))
            raise
    
    def _create_agent_registry_adapter(self) -> AgentRegistry:
        """Create an adapter to bridge CAPP agents with the orchestration package"""
        # This would need to be implemented to adapt CAPP agents to the orchestration package format
        # For now, return a placeholder
        return AgentRegistry()
    
    async def process_payment_flow(
        self, 
        payment_request: Dict[str, Any],
        workflow_type: str = "standard"
    ) -> PaymentResult:
        """
        Process payment using the refactored orchestration
        
        Args:
            payment_request: Payment request data
            workflow_type: Type of workflow to use
            
        Returns:
            PaymentResult: Payment processing result
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                "Starting refactored payment orchestration",
                request_id=payment_request.get("reference_id"),
                workflow_type=workflow_type,
                amount=payment_request.get("amount"),
                from_country=payment_request.get("sender_country"),
                to_country=payment_request.get("recipient_country")
            )
            
            # Select appropriate orchestrator based on workflow type
            orchestrator = self._select_orchestrator(workflow_type, payment_request)
            
            # Process payment through orchestration
            workflow_result = await orchestrator.process_payment(payment_request)
            
            # Convert workflow result to CAPP PaymentResult format
            payment_result = self._convert_workflow_result_to_payment_result(
                workflow_result, 
                payment_request.get("reference_id", str(uuid4())),
                start_time
            )
            
            # Record metrics using existing CAPP metrics collector
            await self._record_payment_metrics(payment_result, start_time)
            
            self.logger.info(
                "Refactored payment orchestration completed",
                payment_id=payment_result.payment_id,
                success=payment_result.success,
                processing_time=payment_result.processing_time if hasattr(payment_result, 'processing_time') else None
            )
            
            return payment_result
            
        except Exception as e:
            self.logger.error(
                "Refactored payment orchestration failed",
                request_id=payment_request.get("reference_id"),
                error=str(e),
                exc_info=True
            )
            
            return PaymentResult(
                success=False,
                payment_id=payment_request.get("reference_id", str(uuid4())),
                status=PaymentStatus.FAILED,
                message=f"Refactored orchestration failed: {str(e)}",
                error_code="REFACTORED_ORCHESTRATION_ERROR"
            )
    
    def _select_orchestrator(
        self, 
        workflow_type: str, 
        payment_request: Dict[str, Any]
    ) -> PaymentWorkflowOrchestrator:
        """Select appropriate orchestrator based on workflow type and payment characteristics"""
        
        # Determine workflow type based on payment characteristics
        amount = Decimal(str(payment_request.get("amount", 0)))
        sender_country = payment_request.get("sender_country")
        recipient_country = payment_request.get("recipient_country")
        
        # High value payments
        if amount > Decimal("10000"):
            self.logger.info("Using high value workflow for large payment", amount=amount)
            return self.high_value_orchestrator
        
        # Fast track for small amounts and trusted corridors
        if amount < Decimal("1000") and self._is_trusted_corridor(sender_country, recipient_country):
            self.logger.info("Using fast track workflow for small trusted payment", amount=amount)
            return self.fast_track_orchestrator
        
        # Compliance heavy for regulated corridors
        if self._is_regulated_corridor(sender_country, recipient_country):
            self.logger.info("Using compliance heavy workflow for regulated corridor")
            return self.compliance_heavy_orchestrator
        
        # Default to standard workflow
        return self.default_orchestrator
    
    def _is_trusted_corridor(self, sender_country: str, recipient_country: str) -> bool:
        """Check if corridor is trusted for fast track processing"""
        trusted_corridors = [
            ("US", "US"), ("KE", "KE"), ("NG", "NG"), ("GB", "GB")
        ]
        return (sender_country, recipient_country) in trusted_corridors
    
    def _is_regulated_corridor(self, sender_country: str, recipient_country: str) -> bool:
        """Check if corridor requires enhanced compliance"""
        regulated_corridors = [
            ("US", "NG"), ("NG", "US"), ("GB", "NG"), ("NG", "GB")
        ]
        return (sender_country, recipient_country) in regulated_corridors
    
    def _convert_workflow_result_to_payment_result(
        self, 
        workflow_result: PaymentWorkflowResult,
        payment_id: str,
        start_time: datetime
    ) -> PaymentResult:
        """Convert workflow result to CAPP PaymentResult format"""
        
        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Extract payment-specific data
        transaction_hash = workflow_result.transaction_hash
        estimated_delivery_time = workflow_result.estimated_delivery_time
        fees_charged = workflow_result.fees_charged
        exchange_rate_used = workflow_result.exchange_rate_used
        
        # Determine payment status
        if workflow_result.success:
            status = PaymentStatus.COMPLETED
            message = "Payment processed successfully"
        else:
            status = PaymentStatus.FAILED
            message = workflow_result.message
        
        return PaymentResult(
            success=workflow_result.success,
            payment_id=payment_id,
            status=status,
            message=message,
            transaction_hash=transaction_hash,
            estimated_delivery_time=estimated_delivery_time,
            fees_charged=fees_charged,
            exchange_rate_used=exchange_rate_used,
            error_code=workflow_result.error_code
        )
    
    async def _record_payment_metrics(
        self, 
        payment_result: PaymentResult,
        start_time: datetime
    ):
        """Record payment metrics using existing CAPP metrics collector"""
        try:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            await self.metrics_collector.record_payment_metrics(
                payment_id=payment_result.payment_id,
                processing_time=processing_time,
                success=payment_result.success,
                status=payment_result.status,
                error_code=payment_result.error_code
            )
        except Exception as e:
            self.logger.warning(f"Failed to record payment metrics: {str(e)}")
    
    async def track_payment_status(self, payment_id: str) -> PaymentStatus:
        """Track payment status using orchestration workflow status"""
        try:
            # This would query the orchestration workflow status
            # For now, return a placeholder
            return PaymentStatus.PENDING
        except Exception as e:
            self.logger.error(f"Failed to track payment status for {payment_id}: {str(e)}")
            return PaymentStatus.FAILED
    
    async def get_payment_analytics(self) -> Dict[str, Any]:
        """Get payment analytics from orchestration metrics"""
        try:
            # Get metrics from all orchestrators
            default_metrics = await self.default_orchestrator.get_payment_workflow_metrics()
            fast_track_metrics = await self.fast_track_orchestrator.get_payment_workflow_metrics()
            high_value_metrics = await self.high_value_orchestrator.get_payment_workflow_metrics()
            compliance_heavy_metrics = await self.compliance_heavy_orchestrator.get_payment_workflow_metrics()
            
            return {
                "default_workflow": default_metrics,
                "fast_track_workflow": fast_track_metrics,
                "high_value_workflow": high_value_metrics,
                "compliance_heavy_workflow": compliance_heavy_metrics,
                "total_workflows": 4
            }
        except Exception as e:
            self.logger.error(f"Failed to get payment analytics: {str(e)}")
            return {}
    
    async def create_custom_workflow(
        self,
        name: str,
        description: str,
        config: PaymentWorkflowConfig
    ) -> PaymentWorkflowOrchestrator:
        """Create a custom payment workflow"""
        try:
            return self.workflow_factory.create_custom_workflow(
                name=name,
                description=description,
                config=config,
                required_agents=[
                    "payment_service",
                    "route_optimization",
                    "compliance",
                    "liquidity",
                    "exchange_rate",
                    "mmo_service",
                    "settlement"
                ]
            )
        except Exception as e:
            self.logger.error(f"Failed to create custom workflow: {str(e)}")
            raise
    
    def get_available_workflow_types(self) -> List[str]:
        """Get available workflow types"""
        return self.workflow_factory.list_workflow_types()
    
    def get_workflow_preset(self, workflow_type: str) -> Optional[Dict[str, Any]]:
        """Get workflow preset configuration"""
        try:
            preset = self.workflow_factory.get_preset(WorkflowType(workflow_type))
            if preset:
                return {
                    "name": preset.name,
                    "description": preset.description,
                    "config": preset.config.dict(),
                    "required_agents": preset.required_agents
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get workflow preset: {str(e)}")
            return None 