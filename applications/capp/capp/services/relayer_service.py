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
    async def execute_route(self, route: Dict[str, Any], user_private_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a cross-chain route using the appropriate bridge adapter.
        """
        bridge_provider = route.get("bridge_provider")
        adapter = self.adapters.get(bridge_provider)
        
        if not adapter:
            raise ValueError(f"Bridge provider '{bridge_provider}' not supported/loaded.")

        logger.info("relayer_execution_started", amount=route.get("amount"), bridge=bridge_provider, chain_path=f"{route.get('from_chain')}->{route.get('to_chain')}")
        
        # 1. Get Quote (Verify bridge is alive + fees)
        quote = await adapter.get_quote(
            from_chain=route["from_chain"],
            to_chain=route["to_chain"],
            token=route["token_in"],
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

        result = await adapter.bridge_assets(
            quote_id=quote["quote_id"],
            private_key=signer_key,
            wallet_address=route.get("recipient", "0x000")
        )

        logger.info("relayer_execution_success", tx_hash=result["tx_hash"])
        return result
