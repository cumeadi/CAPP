import structlog
import asyncio
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

class StellarBridgeClient:
    """
    Mock integration for Stellar for the CAPP Sandbox MVP.
    """
    def __init__(self, horizon_url: str = "https://horizon-testnet.stellar.org"):
        self.horizon_url = horizon_url
        self.is_connected = False
        
    async def connect(self):
        logger.info("stellar_bridge_connecting", url=self.horizon_url)
        await asyncio.sleep(0.1) # Simulate connection time 
        self.is_connected = True
        return self
        
    async def get_balance(self, public_key: str) -> float:
        """Return a mock XLM balance."""
        if not self.is_connected:
             await self.connect()
        # Mock testnet account balances
        return 50000.00

    async def execute_payment(self, recipient: str, amount: float, asset_code: str = "XLM") -> str:
        """Simulates native XLM or issued asset payments on Stellar."""
        if not self.is_connected:
             await self.connect()
             
        logger.info("stellar_payment_initiated", recipient=recipient, amount=amount, asset=asset_code)
        await asyncio.sleep(0.5) # Fast block times (~5s real, 0.5s mock)
        
        import uuid
        return f"xlm_tx_{uuid.uuid4().hex[:16]}"

# Global lazy mock client
_stellar_client = None

def get_stellar_client() -> StellarBridgeClient:
    global _stellar_client
    if not _stellar_client:
        _stellar_client = StellarBridgeClient()
    return _stellar_client
