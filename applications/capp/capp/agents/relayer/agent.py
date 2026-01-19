from typing import Optional, Dict, Any
from decimal import Decimal
import structlog

from applications.capp.capp.agents.base import BasePaymentAgent, AgentConfig, AgentState
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentResult, PaymentStatus
from applications.capp.capp.services.relayer_service import RelayerService

logger = structlog.get_logger(__name__)

class RelayerAgentConfig(AgentConfig):
    """Configuration for Relayer Agent"""
    agent_type: str = "relayer"
    supported_bridges: list[str] = ["MockBridge"]

class RelayerAgent(BasePaymentAgent):
    """
    Agent responsible for executing cross-chain payment routes.
    """
    
    def __init__(self, config: RelayerAgentConfig):
        super().__init__(config)
        self.relayer_service = RelayerService()
        
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        """
        Validate if we can relay this payment.
        For MVP: Accept everything.
        """
        if payment.amount <= 0:
            return False
            
        return True

    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Execute the payment using RelayerService.
        """
        self.logger.info("relayer_agent_processing", payment_id=payment.payment_id)
        
        try:
            # 1. Construct Route context from Payment
            # In a full routing flow, the 'route' might already be attached to the payment metadata.
            # If not, we might need to *ask* the RoutingService or assume a default path.
            # For this MVP, we look for 'route_details' in the payment metadata, or construct a default.
            
            route_details = payment.metadata.get("route_details")
            
            if not route_details:
                # Fallback / Auto-Construct for direct payments
                # Assuming this is a direct execution request without prior routing step
                route_details = {
                    "bridge_provider": "MockBridge",
                    "from_chain": "Aptos", # Default source
                    "to_chain": "Polygon", # Default dest
                    "token_in": payment.source_currency,
                    "token_out": payment.target_currency,
                    "amount": float(payment.amount),
                    "recipient": payment.recipient_id # Assuming recipient_id is wallet address
                }
                self.logger.info("relayer_auto_constructed_route", route=route_details)

            # 2. Execute via Service
            result = await self.relayer_service.execute_route(
                route=route_details,
                user_private_key=None # Use defaults/agent keys
            )
            
            # 3. Handle Result
            if result["status"] == "COMPLETED":
                return PaymentResult(
                    success=True,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.COMPLETED,
                    transaction_hash=result["tx_hash"],
                    message=f"Cross-chain relay successful. Explorer: {result['explorer_url']}"
                )
            else:
                 return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=f"Bridge returned status: {result['status']}",
                    error_code="BRIDGE_FAILURE"
                )

        except Exception as e:
            self.logger.error("relayer_agent_failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=str(e),
                error_code="RELAYER_EXCEPTION"
            )
