import structlog
from typing import Dict, Optional, Any
from decimal import Decimal
from applications.capp.capp.adapters.bridge_base import BaseBridgeAdapter
from applications.capp.capp.adapters.mock_bridge import MockBridgeAdapter
from applications.capp.capp.core.chaos import chaos_inject
from applications.capp.capp.config.settings import settings

logger = structlog.get_logger(__name__)

class RelayerService:
    """
    Execution Arm of the Routing Engine.
    Signs and submits transactions via Bridge Adapters.
    """

    def __init__(self):
        self.adapters: Dict[str, BaseBridgeAdapter] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default adapters."""
        # In production, we might conditionally load these based on config
        self.register_adapter(MockBridgeAdapter())

    def register_adapter(self, adapter: BaseBridgeAdapter):
        self.adapters[adapter.name] = adapter
        logger.info("bridge_adapter_registered", name=adapter.name)

    def get_adapter(self, name: str) -> Optional[BaseBridgeAdapter]:
        return self.adapters.get(name)

    @chaos_inject
    async def execute_route(self, route: Dict[str, Any], user_private_key: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a cross-chain route using the appropriate bridge adapter.
        Requires a valid API Key for billing.
        """
        # 0. Billing & Authorization
        from applications.capp.capp.services.billing_service import BillingService
        billing = BillingService.get_instance()
        
        if not api_key:
             raise ValueError("API Key is required for Relayer execution.")
             
        # Authorize
        account_id = billing.authorize(api_key)
        
        # Estimate Cost (Mocked flat fee for MVP)
        ESTIMATED_FEE = Decimal("0.50") # $0.50 per tx
        
        # Check Credits
        if not billing.check_credits(account_id, ESTIMATED_FEE):
            raise ValueError(f"Insufficient credits. Execution requires ${ESTIMATED_FEE}")

        bridge_provider = route.get("bridge_provider")
        adapter = self.adapters.get(bridge_provider)
        
        if not adapter:
            raise ValueError(f"Bridge provider '{bridge_provider}' not supported/loaded.")

        logger.info("relayer_execution_started", amount=route.get("amount"), bridge=bridge_provider, chain_path=f"{route.get('from_chain')}->{route.get('to_chain')}", account_id=account_id)
        
        # 1. Get Quote (Verify bridge is alive + fees)
        quote = await adapter.get_quote(
            from_chain=route["from_chain"],
            to_chain=route["to_chain"],
            token_in=route["token_in"],
            token_out=route.get("token_out", route["token_in"]), # Default to same token if not specified
            amount=route["amount"]
        )

        # 2. Execute Bridge
        # NOTE: In production, we would never pass raw keys around like this.
        # We would use a KMS or secure signer service.
        # This is for the "Agent" context where the agent holds a session key.
        signer_key = user_private_key or settings.APTOS_PRIVATE_KEY # Fallback to agent key
        
        if not signer_key:
             # Even mock execution needs a "concept" of a signer
             signer_key = "mock_key_123" 

        # 2a. Notify Oracle (Pending) - If we had a deterministic hash pre-broadcast, we'd index it here.
        # For now, we update post-broadcast.

        try:
            result = await adapter.bridge_assets(
                quote_id=quote["quote_id"],
                private_key=signer_key,
                wallet_address=route.get("recipient", "0x000")
            )
            
            # 3. Bill the User
            billing.deduct_credits(account_id, ESTIMATED_FEE)
            
            # 4. Notify Oracle (Completed)
            from applications.capp.capp.services.oracle_service import OracleService, TransactionStatus
            oracle = OracleService.get_instance()
            await oracle.update_index(
                tx_hash=result["tx_hash"], 
                status=TransactionStatus.COMPLETED,
                meta={
                    "chain": route["to_chain"],
                    "fee": float(ESTIMATED_FEE),
                    "account_id": account_id
                }
            )

            logger.info("relayer_execution_success", tx_hash=result["tx_hash"], fee_charged=float(ESTIMATED_FEE))

            result["fee_charged"] = float(ESTIMATED_FEE)
            return result
            
        except Exception as e:
            # If we had a partial hash, we'd mark FAILED. 
            # Since we failed before/during bridging, we rely on the Exception bubbling up.
            logger.error("relayer_execution_failed", error=str(e))
            raise e
