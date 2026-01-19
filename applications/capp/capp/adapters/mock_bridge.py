import asyncio
import uuid
import structlog
from typing import Dict, Any
from decimal import Decimal
from .bridge_base import BaseBridgeAdapter

logger = structlog.get_logger(__name__)

class MockBridgeAdapter(BaseBridgeAdapter):
    """
    Simulates cross-chain transfers without real execution.
    Useful for testing the Relayer Logic and UI flows.
    """

    @property
    def name(self) -> str:
        return "MockBridge"

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount: Decimal,
        from_chain: str,
        to_chain: str
    ) -> Dict[str, Any]:
        """
        Returns a hardcoded, fast quote.
        """
        fee = Decimal("0.50") # USD
        
        return {
            "fee_usd": float(fee),
            "estimated_time_seconds": 30,
            "provider": "MockBridge",
            "quote_id": f"mock_quote_{uuid.uuid4()}",
            "amount_in": str(amount),
            "amount_out": str(amount), # 1:1 simulation
            "meta": {
                "path": f"{from_chain}->{to_chain}"
            }
        }

    async def bridge_assets(
        self,
        quote_id: str,
        private_key: str, 
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Simulate a transaction delay and return a fake hash.
        """
        logger.info("mock_bridging_started", quote_id=quote_id, recipient=wallet_address)
        
        # Simulate network latency
        await asyncio.sleep(2)
        
        tx_hash = f"0xmock{uuid.uuid4().hex}"
        logger.info("mock_bridging_completed", tx_hash=tx_hash)
        
        return {
            "tx_hash": tx_hash,
            "status": "COMPLETED",
            "explorer_url": f"https://mockscan.io/tx/{tx_hash}"
        }
