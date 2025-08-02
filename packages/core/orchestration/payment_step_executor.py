"""
Payment Step Executor

This module provides specialized executors for payment processing steps,
extracting the step-specific logic from CAPP into reusable components.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import structlog

from pydantic import BaseModel, Field

from packages.core.agents.base import BaseFinancialAgent, ProcessingResult
from packages.core.agents.financial_base import FinancialTransaction
from packages.core.orchestration.payment_workflow_orchestrator import PaymentWorkflowStep


logger = structlog.get_logger(__name__)


class PaymentStepContext(BaseModel):
    """Context for payment step execution"""
    payment_id: str
    step_id: str
    step_name: str
    payment_data: Dict[str, Any]
    step_results: Dict[str, ProcessingResult] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentStepResult(BaseModel):
    """Result of payment step execution"""
    success: bool
    step_id: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    processing_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentStepExecutor:
    """
    Base class for payment step executors
    
    Provides common functionality for executing payment processing steps
    and handling step-specific logic.
    """
    
    def __init__(self, step_id: str, step_name: str):
        self.step_id = step_id
        self.step_name = step_name
        self.logger = structlog.get_logger(__name__)
    
    async def execute(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """
        Execute the payment step
        
        Args:
            context: Payment step context
            agents: Available agents for this step
            
        Returns:
            PaymentStepResult: Step execution result
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                f"Executing payment step: {self.step_name}",
                payment_id=context.payment_id,
                step_id=self.step_id
            )
            
            # Execute step-specific logic
            result = await self._execute_step(context, agents)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.info(
                f"Payment step completed: {self.step_name}",
                payment_id=context.payment_id,
                step_id=self.step_id,
                success=result.success,
                processing_time=processing_time
            )
            
            return PaymentStepResult(
                success=result.success,
                step_id=self.step_id,
                message=result.message,
                data=result.data,
                error_code=result.error_code,
                processing_time=processing_time,
                metadata=result.metadata
            )
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                f"Payment step failed: {self.step_name}",
                payment_id=context.payment_id,
                step_id=self.step_id,
                error=str(e),
                exc_info=True
            )
            
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Step execution failed: {str(e)}",
                error_code="STEP_EXECUTION_ERROR",
                processing_time=processing_time
            )
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Execute step-specific logic - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _execute_step")


class CreatePaymentStepExecutor(PaymentStepExecutor):
    """Executor for payment creation step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.CREATE_PAYMENT, "Create Payment")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Create and validate payment object"""
        try:
            payment_request = context.payment_data.get("payment_request", {})
            
            # Validate required fields
            required_fields = ["reference_id", "amount", "from_currency", "to_currency"]
            for field in required_fields:
                if not payment_request.get(field):
                    return PaymentStepResult(
                        success=False,
                        step_id=self.step_id,
                        message=f"Missing required field: {field}",
                        error_code="MISSING_REQUIRED_FIELD"
                    )
            
            # Create payment object
            payment_data = {
                "payment_id": payment_request["reference_id"],
                "amount": Decimal(str(payment_request["amount"])),
                "from_currency": payment_request["from_currency"],
                "to_currency": payment_request["to_currency"],
                "payment_type": payment_request.get("payment_type", "personal_remittance"),
                "payment_method": payment_request.get("payment_method", "mobile_money"),
                "sender": {
                    "name": payment_request.get("sender_name", ""),
                    "phone_number": payment_request.get("sender_phone", ""),
                    "country": payment_request.get("sender_country", "")
                },
                "recipient": {
                    "name": payment_request.get("recipient_name", ""),
                    "phone_number": payment_request.get("recipient_phone", ""),
                    "country": payment_request.get("recipient_country", "")
                },
                "status": "created",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Payment created successfully",
                data={"payment": payment_data},
                metadata={"payment_id": payment_request["reference_id"]}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Failed to create payment: {str(e)}",
                error_code="PAYMENT_CREATION_FAILED"
            )


class ValidatePaymentStepExecutor(PaymentStepExecutor):
    """Executor for payment validation step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.VALIDATE_PAYMENT, "Validate Payment")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Validate payment data and business rules"""
        try:
            # Get payment data from previous step
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Validate amount
            amount = payment_data.get("amount", 0)
            if amount <= 0:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment amount must be greater than zero",
                    error_code="INVALID_AMOUNT"
                )
            
            # Validate currencies
            from_currency = payment_data.get("from_currency")
            to_currency = payment_data.get("to_currency")
            if from_currency == to_currency:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Source and destination currencies must be different",
                    error_code="SAME_CURRENCY"
                )
            
            # Validate corridor support (simplified)
            sender_country = payment_data.get("sender", {}).get("country")
            recipient_country = payment_data.get("recipient", {}).get("country")
            
            # Check if corridor is supported
            supported_corridors = [
                ("US", "KE"), ("KE", "US"), ("US", "NG"), ("NG", "US"),
                ("GB", "KE"), ("KE", "GB"), ("GB", "NG"), ("NG", "GB")
            ]
            
            corridor = (sender_country, recipient_country)
            if corridor not in supported_corridors:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message=f"Corridor {sender_country} -> {recipient_country} not supported",
                    error_code="UNSUPPORTED_CORRIDOR"
                )
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Payment validation successful",
                data={"validation_passed": True},
                metadata={"corridor": corridor}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Payment validation failed: {str(e)}",
                error_code="VALIDATION_FAILED"
            )


class OptimizeRouteStepExecutor(PaymentStepExecutor):
    """Executor for route optimization step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.OPTIMIZE_ROUTE, "Optimize Route")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Optimize payment route"""
        try:
            # Get payment data
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Find route optimization agent
            route_agent = None
            for agent in agents:
                if agent.agent_type == "route_optimization":
                    route_agent = agent
                    break
            
            if not route_agent:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="No route optimization agent available",
                    error_code="AGENT_NOT_AVAILABLE"
                )
            
            # Create transaction for route optimization
            transaction = FinancialTransaction(
                transaction_id=context.payment_id,
                transaction_type="route_optimization",
                amount=payment_data.get("amount", 0),
                currency=payment_data.get("from_currency", "USD"),
                metadata={
                    "payment_data": payment_data,
                    "step_id": self.step_id
                }
            )
            
            # Execute route optimization
            result = await route_agent.process_transaction(transaction)
            
            if not result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message=f"Route optimization failed: {result.message}",
                    error_code="ROUTE_OPTIMIZATION_FAILED"
                )
            
            # Extract route data
            route_data = result.metadata.get("route", {})
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Route optimization completed",
                data={"route": route_data},
                metadata={"selected_route": route_data}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Route optimization failed: {str(e)}",
                error_code="ROUTE_OPTIMIZATION_ERROR"
            )


class ValidateComplianceStepExecutor(PaymentStepExecutor):
    """Executor for compliance validation step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.VALIDATE_COMPLIANCE, "Validate Compliance")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Validate compliance requirements"""
        try:
            # Find compliance agent
            compliance_agent = None
            for agent in agents:
                if agent.agent_type == "compliance":
                    compliance_agent = agent
                    break
            
            if not compliance_agent:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="No compliance agent available",
                    error_code="AGENT_NOT_AVAILABLE"
                )
            
            # Get payment data
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Create transaction for compliance check
            transaction = FinancialTransaction(
                transaction_id=context.payment_id,
                transaction_type="compliance_check",
                amount=payment_data.get("amount", 0),
                currency=payment_data.get("from_currency", "USD"),
                metadata={
                    "payment_data": payment_data,
                    "step_id": self.step_id
                }
            )
            
            # Execute compliance check
            result = await compliance_agent.process_transaction(transaction)
            
            if not result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message=f"Compliance validation failed: {result.message}",
                    error_code="COMPLIANCE_VALIDATION_FAILED"
                )
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Compliance validation passed",
                data={"compliance_passed": True},
                metadata={"compliance_result": result.metadata}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Compliance validation failed: {str(e)}",
                error_code="COMPLIANCE_VALIDATION_ERROR"
            )


class CheckLiquidityStepExecutor(PaymentStepExecutor):
    """Executor for liquidity check step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.CHECK_LIQUIDITY, "Check Liquidity")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Check liquidity availability"""
        try:
            # Find liquidity agent
            liquidity_agent = None
            for agent in agents:
                if agent.agent_type == "liquidity":
                    liquidity_agent = agent
                    break
            
            if not liquidity_agent:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="No liquidity agent available",
                    error_code="AGENT_NOT_AVAILABLE"
                )
            
            # Get payment data
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Create transaction for liquidity check
            transaction = FinancialTransaction(
                transaction_id=context.payment_id,
                transaction_type="liquidity_check",
                amount=payment_data.get("amount", 0),
                currency=payment_data.get("from_currency", "USD"),
                metadata={
                    "payment_data": payment_data,
                    "step_id": self.step_id
                }
            )
            
            # Execute liquidity check
            result = await liquidity_agent.process_transaction(transaction)
            
            if not result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message=f"Liquidity check failed: {result.message}",
                    error_code="INSUFFICIENT_LIQUIDITY"
                )
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Liquidity check passed",
                data={"liquidity_available": True},
                metadata={"liquidity_result": result.metadata}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Liquidity check failed: {str(e)}",
                error_code="LIQUIDITY_CHECK_ERROR"
            )


class LockExchangeRateStepExecutor(PaymentStepExecutor):
    """Executor for exchange rate locking step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.LOCK_EXCHANGE_RATE, "Lock Exchange Rate")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Lock exchange rate for payment"""
        try:
            # Find exchange rate agent
            exchange_agent = None
            for agent in agents:
                if agent.agent_type == "exchange_rate":
                    exchange_agent = agent
                    break
            
            if not exchange_agent:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="No exchange rate agent available",
                    error_code="AGENT_NOT_AVAILABLE"
                )
            
            # Get payment data
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Create transaction for exchange rate locking
            transaction = FinancialTransaction(
                transaction_id=context.payment_id,
                transaction_type="exchange_rate_lock",
                amount=payment_data.get("amount", 0),
                currency=payment_data.get("from_currency", "USD"),
                metadata={
                    "payment_data": payment_data,
                    "to_currency": payment_data.get("to_currency"),
                    "step_id": self.step_id
                }
            )
            
            # Execute exchange rate locking
            result = await exchange_agent.process_transaction(transaction)
            
            if not result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message=f"Exchange rate locking failed: {result.message}",
                    error_code="EXCHANGE_RATE_LOCK_FAILED"
                )
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Exchange rate locked successfully",
                data={"exchange_rate_locked": True},
                metadata={"exchange_rate_result": result.metadata}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Exchange rate locking failed: {str(e)}",
                error_code="EXCHANGE_RATE_LOCK_ERROR"
            )


class ExecuteMMOStepExecutor(PaymentStepExecutor):
    """Executor for MMO execution step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.EXECUTE_MMO, "Execute MMO Payment")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Execute MMO payment"""
        try:
            # Find MMO agent
            mmo_agent = None
            for agent in agents:
                if agent.agent_type == "mmo_service":
                    mmo_agent = agent
                    break
            
            if not mmo_agent:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="No MMO agent available",
                    error_code="AGENT_NOT_AVAILABLE"
                )
            
            # Get payment data
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Create transaction for MMO execution
            transaction = FinancialTransaction(
                transaction_id=context.payment_id,
                transaction_type="mmo_execution",
                amount=payment_data.get("amount", 0),
                currency=payment_data.get("from_currency", "USD"),
                metadata={
                    "payment_data": payment_data,
                    "step_id": self.step_id
                }
            )
            
            # Execute MMO payment
            result = await mmo_agent.process_transaction(transaction)
            
            if not result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message=f"MMO execution failed: {result.message}",
                    error_code="MMO_EXECUTION_FAILED"
                )
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="MMO payment executed successfully",
                data={"mmo_executed": True},
                metadata={"mmo_result": result.metadata}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"MMO execution failed: {str(e)}",
                error_code="MMO_EXECUTION_ERROR"
            )


class SettlePaymentStepExecutor(PaymentStepExecutor):
    """Executor for payment settlement step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.SETTLE_PAYMENT, "Settle Payment")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Settle payment on blockchain"""
        try:
            # Find settlement agent
            settlement_agent = None
            for agent in agents:
                if agent.agent_type == "settlement":
                    settlement_agent = agent
                    break
            
            if not settlement_agent:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="No settlement agent available",
                    error_code="AGENT_NOT_AVAILABLE"
                )
            
            # Get payment data
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Create transaction for settlement
            transaction = FinancialTransaction(
                transaction_id=context.payment_id,
                transaction_type="payment_settlement",
                amount=payment_data.get("amount", 0),
                currency=payment_data.get("from_currency", "USD"),
                metadata={
                    "payment_data": payment_data,
                    "step_id": self.step_id
                }
            )
            
            # Execute settlement
            result = await settlement_agent.process_transaction(transaction)
            
            if not result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message=f"Payment settlement failed: {result.message}",
                    error_code="SETTLEMENT_FAILED"
                )
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Payment settled successfully",
                data={"settlement_completed": True},
                metadata={"settlement_result": result.metadata}
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Payment settlement failed: {str(e)}",
                error_code="SETTLEMENT_ERROR"
            )


class ConfirmPaymentStepExecutor(PaymentStepExecutor):
    """Executor for payment confirmation step"""
    
    def __init__(self):
        super().__init__(PaymentWorkflowStep.CONFIRM_PAYMENT, "Confirm Payment")
    
    async def _execute_step(
        self, 
        context: PaymentStepContext,
        agents: List[BaseFinancialAgent]
    ) -> PaymentStepResult:
        """Confirm payment completion"""
        try:
            # Get payment data
            create_step_result = context.step_results.get(PaymentWorkflowStep.CREATE_PAYMENT)
            if not create_step_result or not create_step_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment creation step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            payment_data = create_step_result.data.get("payment", {})
            
            # Get settlement result
            settlement_result = context.step_results.get(PaymentWorkflowStep.SETTLE_PAYMENT)
            if not settlement_result or not settlement_result.success:
                return PaymentStepResult(
                    success=False,
                    step_id=self.step_id,
                    message="Payment settlement step must be completed first",
                    error_code="PREREQUISITE_STEP_FAILED"
                )
            
            # Update payment status
            payment_data["status"] = "completed"
            payment_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            # Extract transaction hash from settlement
            transaction_hash = settlement_result.metadata.get("settlement_result", {}).get("transaction_hash")
            
            return PaymentStepResult(
                success=True,
                step_id=self.step_id,
                message="Payment confirmed successfully",
                data={
                    "payment_confirmed": True,
                    "final_payment_data": payment_data
                },
                metadata={
                    "transaction_hash": transaction_hash,
                    "completion_time": payment_data["completed_at"]
                }
            )
            
        except Exception as e:
            return PaymentStepResult(
                success=False,
                step_id=self.step_id,
                message=f"Payment confirmation failed: {str(e)}",
                error_code="CONFIRMATION_ERROR"
            )


# Step executor registry
STEP_EXECUTORS = {
    PaymentWorkflowStep.CREATE_PAYMENT: CreatePaymentStepExecutor(),
    PaymentWorkflowStep.VALIDATE_PAYMENT: ValidatePaymentStepExecutor(),
    PaymentWorkflowStep.OPTIMIZE_ROUTE: OptimizeRouteStepExecutor(),
    PaymentWorkflowStep.VALIDATE_COMPLIANCE: ValidateComplianceStepExecutor(),
    PaymentWorkflowStep.CHECK_LIQUIDITY: CheckLiquidityStepExecutor(),
    PaymentWorkflowStep.LOCK_EXCHANGE_RATE: LockExchangeRateStepExecutor(),
    PaymentWorkflowStep.EXECUTE_MMO: ExecuteMMOStepExecutor(),
    PaymentWorkflowStep.SETTLE_PAYMENT: SettlePaymentStepExecutor(),
    PaymentWorkflowStep.CONFIRM_PAYMENT: ConfirmPaymentStepExecutor(),
}


def get_step_executor(step_id: str) -> Optional[PaymentStepExecutor]:
    """Get step executor for the given step ID"""
    return STEP_EXECUTORS.get(step_id) 